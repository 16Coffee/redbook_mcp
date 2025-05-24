"""
笔记相关功能模块，包括搜索、获取内容等
"""
import asyncio
import json
import re
from src.core.base.utils import extract_text, parse_note_content, detect_domain, extract_keywords


class NoteManager:
    """笔记管理类，处理笔记的搜索、获取内容等操作"""
    
    def __init__(self, browser_manager):
        """初始化笔记管理器
        
        Args:
            browser_manager: 浏览器管理器实例
        """
        self.browser = browser_manager
    
    async def search_notes(self, keywords, limit=5):
        """根据关键词搜索笔记
        
        Args:
            keywords (str): 搜索关键词
            limit (int, optional): 返回结果数量限制. 默认为5.
        
        Returns:
            str: 搜索结果
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号"
        
        # 构建搜索URL并访问
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={keywords}"
        try:
            await self.browser.goto(search_url, wait_time=5)
            
            # 获取帖子卡片
            post_cards = await self.browser.main_page.query_selector_all('section.note-item')
            
            if not post_cards:
                # 尝试备用选择器
                post_cards = await self.browser.main_page.query_selector_all('div[data-v-a264b01a]')
            
            post_data = []
            found_count = 0
            
            for card in post_cards:
                if found_count >= limit:
                    break
                    
                try:
                    # 获取链接
                    link_element = await card.query_selector('a[href*="/search_result/"]')
                    if not link_element:
                        continue
                    
                    href = await link_element.get_attribute('href')
                    if href and '/search_result/' in href:
                        # 尝试从URL中提取笔记ID，并构造正确的explore URL
                        import re
                        
                        # 提取笔记ID（通常在search_result/后面）
                        note_id_match = re.search(r'/search_result/([a-f0-9]+)', href)
                        if note_id_match:
                            note_id = note_id_match.group(1)
                            
                            # 提取xsec_token参数
                            xsec_token_match = re.search(r'xsec_token=([^&]+)', href)
                            if xsec_token_match:
                                xsec_token = xsec_token_match.group(1)
                                # 构造explore格式的URL
                                full_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source="
                            else:
                                # 如果没有xsec_token，使用原始URL
                                full_url = f"https://www.xiaohongshu.com{href}"
                        else:
                            # 如果无法提取ID，使用原始URL
                            full_url = f"https://www.xiaohongshu.com{href}"
                        
                        # 获取标题
                        title = await self._extract_card_title(card)
                        
                        post_data.append({
                            "序号": len(post_data) + 1,
                            "标题": title,
                            "链接": full_url
                        })
                        
                        found_count += 1
                        
                except Exception as e:
                    continue
            
            # 如果找不到任何内容，返回提示
            if not post_data:
                return f"未找到与 '{keywords}' 相关的笔记，请尝试其他关键词。"
            
            # 格式化输出
            result = f"找到 {len(post_data)} 条与 '{keywords}' 相关的笔记：\n\n"
            for item in post_data:
                result += f"{item['序号']}. 标题: {item['标题']}\n   链接: {item['链接']}\n\n"
            
            return result
        
        except Exception as e:
            return f"搜索笔记时出错: {str(e)}"
    
    async def _extract_card_title(self, card):
        """从帖子卡片中提取标题
        
        Args:
            card: 帖子卡片元素
        
        Returns:
            str: 提取的标题
        """
        # More specific selectors first, ordered by likely precision
        selectors_to_try = [
            'a span.title-content',                 # Specific class within an anchor
            'a div.title-content',                  # Specific class within an anchor (div variant)
            'a[href*="/explore/"] span[class*="title"]', # Title-like span within an explore link
            'div.note-card-title',                  # Common specific class for note titles
            '.title span',                          # Generic title class with a span inside
            'a.title',                              # Anchor with title class
            'div.footer a.title span',              # Existing selector (kept as a fallback)
            'span.note-title-text',                 # Another possible specific class for title text
        ]

        for selector in selectors_to_try:
            title_element = await card.query_selector(selector)
            if title_element:
                title = await title_element.text_content()
                if title and title.strip() and len(title.strip()) > 3: # Ensure title is somewhat substantial
                    return title.strip()

        # Fallback: Check common text containers if specific title classes fail
        # Prioritize elements that are more likely to contain titles.
        common_text_containers = await card.query_selector_all(
            'a span, a div, h2, h3, p[class*="name"], p[class*="desc"]' # More targeted than just 'span'
        )
        potential_titles = []
        for text_el in common_text_containers:
            text = await text_el.text_content()
            if text and len(text.strip()) > 5: # Keep minimum length check
                potential_titles.append(text.strip())
        
        if potential_titles:
            # Choose the longest, most relevant-looking text
            # Simple heuristic: longer is often better for titles.
            return max(potential_titles, key=len)
        
        # Optimized JavaScript fallback (if absolutely necessary)
        # This is a last resort and should ideally be avoided by strong Python selectors.
        try:
            js_title = await card.evaluate('''
                el => {
                    // Try specific, then less specific, common title patterns
                    const selectors = [
                        'a span.title-content', 'a div.title-content', // Specific structure
                        '.note-card-title', '.title',                   // Common title classes
                        'meta[property="og:title"]', 'meta[name="twitter:title"]', // Meta tags (less likely in card context)
                        'h2', 'h3',                                     // Heading tags
                        'a[href*="/explore/"] > div', 'a[href*="/explore/"] > span' // Direct children of links
                    ];
                    for (const selector of selectors) {
                        const foundEl = el.querySelector(selector);
                        if (foundEl && foundEl.textContent && foundEl.textContent.trim().length > 3) {
                            return foundEl.textContent.trim();
                        }
                    }
                    // Fallback to finding the longest text in common elements
                    const candidates = Array.from(el.querySelectorAll('a, p, span, div'));
                    let longestText = '';
                    for (const cand of candidates) {
                        const text = cand.textContent ? cand.textContent.trim() : '';
                        if (text.length > longestText.length && text.length > 5) {
                            longestText = text;
                        }
                    }
                    return longestText || null;
                }
            ''')
            if js_title:
                return js_title
        except Exception as e:
            # print(f"JavaScript fallback for title extraction failed: {e}") # Optional logging
            pass
        
        return "未知标题" # Default if all else fails
    
    async def _extract_images(self):
        """提取笔记图片
        
        Returns:
            list: 图片URL列表
        """
        try:
            images = await self.browser.main_page.evaluate('''
                () => {
                    // 获取所有图片元素
                    const imageElements = document.querySelectorAll('.note-content img, .carousel img');
                    
                    // 提取图片URL
                    return Array.from(imageElements)
                        .map(img => img.src)
                        .filter(src => src && src.trim().length > 0);
                }
            ''')
            
            return images if images else []
        except:
            return []
    
    async def get_note_content(self, url):
        """获取笔记内容
        
        Args:
            url (str): 笔记 URL
        
        Returns:
            str: 结构化笔记内容
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号"
        
        try:
            # 访问帖子链接
            await self.browser.goto(url, wait_time=8)
            
            # 滚动页面以确保加载所有内容
            await self.browser.main_page.evaluate('''
                () => {
                    window.scrollTo(0, document.body.scrollHeight);
                    setTimeout(() => { window.scrollTo(0, document.body.scrollHeight / 2); }, 1000);
                    setTimeout(() => { window.scrollTo(0, 0); }, 2000);
                }
            ''')
            await self.browser.main_page.wait_for_timeout(3000)
            
            # 获取笔记信息
            note_info = await self.browser.main_page.evaluate('''
                () => {
                    // 尝试获取标题
                    let title = "";
                    const titleSelectors = ['#detail-title', 'div.title', 'h1', 'div.note-content div.title'];
                    for (const selector of titleSelectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent.trim()) {
                            title = el.textContent.trim();
                            break;
                        }
                    }
                    
                    // 尝试获取作者
                    let author = "";
                    const authorSelectors = ['.user-nickname', '.author-nickname', '.nickname', 'span.username', 'a.user-info'];
                    for (const selector of authorSelectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent.trim()) {
                            author = el.textContent.trim();
                            break;
                        }
                    }
                    
                    // 尝试获取内容
                    let content = "";
                    const contentSelectors = ['.note-content', '#detail-desc', 'div.content', 'div.desc'];
                    for (const selector of contentSelectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent.trim()) {
                            content = el.textContent.trim();
                            break;
                        }
                    }
                    
                    return {
                        title: title || "未知标题",
                        author: author || "未知作者",
                        content: content || "未能获取内容"
                    };
                }
            ''')
            
            # 拼接结构化字符串
            result = f"标题: {note_info['title']}\n作者: {note_info['author']}\n内容: {note_info['content']}"
            return result
        except Exception as e:
            return f"获取笔记内容时出错: {str(e)}"
    
    async def get_note_comments(self, url):
        """获取笔记评论
        
        Args:
            url (str): 笔记 URL
        
        Returns:
            str: 评论内容
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号"
        
        try:
            # 访问帖子链接
            await self.browser.goto(url, wait_time=5)
            
            # 先滚动到评论区
            comment_section_locators = [
                {'type': 'text', 'value': '条评论'},
                {'type': 'text', 'value': '评论'},
                {'type': 'selector', 'value': 'div.comment-list'},
                {'type': 'selector', 'value': 'div.comments-container'}
            ]
            
            for locator in comment_section_locators:
                try:
                    if locator['type'] == 'text':
                        comment_section = await self.browser.main_page.query_selector(f'text="{locator["value"]}"')
                    else:
                        comment_section = await self.browser.main_page.query_selector(locator['value'])
                    
                    if comment_section:
                        # 使用JavaScript滚动到元素
                        await self.browser.main_page.evaluate('''
                            (element) => {
                                element.scrollIntoView({ behavior: "smooth", block: "center" });
                            }
                        ''', comment_section)
                        
                        await self.browser.main_page.wait_for_selector('div.comment-item, div.commentItem', timeout=5000, state='attached')
                        
                        # 尝试点击评论区
                        try:
                            await comment_section.click()
                            await self.browser.main_page.wait_for_timeout(2000)
                        except Exception:
                            pass
                        
                        break
                except Exception:
                    continue
            
            # 滚动页面以加载更多评论
            for i in range(8):
                try:
                    await self.browser.main_page.evaluate("window.scrollBy(0, 500)")
                    await self.browser.main_page.wait_for_timeout(1000)
                    
                    # 尝试点击"查看更多评论"按钮
                    more_comment_selectors = [
                        'text="查看更多评论"',
                        'text="展开更多评论"',
                        'text="加载更多"',
                        'text="查看全部"'
                    ]
                    
                    for selector in more_comment_selectors:
                        try:
                            more_btn = await self.browser.main_page.query_selector(selector)
                            if more_btn and await more_btn.is_visible():
                                initial_comment_count = await self.browser.main_page.evaluate("document.querySelectorAll('.comment-item, .commentItem').length")
                                await more_btn.click()
                                await self.browser.main_page.wait_for_function(f"document.querySelectorAll('.comment-item, .commentItem').length > {initial_comment_count}", timeout=5000)
                        except Exception:
                            continue
                except Exception:
                    pass
            
            # 获取评论
            comments = []
            
            # 使用特定评论选择器 - Prioritized and expanded list
            comment_selectors = [
                "div.comment-item",             # Common class for a single comment
                "div.commentItem",              # Alternative common class
                ".comment-root",                # Root element of a comment
                "div.normal-comment-item",      # Specific type of comment item
                "div.sub-comment-item",         # For replies or sub-comments
                "div.comment-content-container",# Container for the comment's actual content
                "div.comment-wrapper",          # General wrapper
                "section.comment",              # Semantic tag for comment
                "div.feed-comment",             # Comments in a feed-like structure
                # Fallback to less specific if above fail
                "div[class*='comment']",        # Any div with 'comment' in its class
            ]
            
            for selector in comment_selectors:
                comment_elements = await self.browser.main_page.query_selector_all(selector)
                if comment_elements and len(comment_elements) > 0:
                    for comment_element in comment_elements:
                        try:
                            # 提取评论者名称 - Prioritized and refined
                            username = "未知用户"
                            username_selectors = [
                                "a.user-name",          # Anchor with user-name class (high priority)
                                "span.user-name",       # Span with user-name class
                                ".name",                # Generic .name class (often used for usernames)
                                ".nick-name",           # Common alternative for nickname
                                ".nickname",            # General nickname class
                                "a[href*='/user/profile'] > span", # Username span directly under a profile link
                                "div.user-info a",      # Username link within a user-info div
                            ]
                            for username_selector in username_selectors:
                                username_el = await comment_element.query_selector(username_selector)
                                if username_el:
                                    username_text = await username_el.text_content()
                                    if username_text and username_text.strip():
                                        username = username_text.strip()
                                        break
                            
                            # 如果主要选择器未找到，尝试直接从用户链接（作为后备）
                            if username == "未知用户":
                                user_link = await comment_element.query_selector('a[href*="/user/profile/"]')
                                if user_link:
                                    username_text = await user_link.text_content()
                                    if username_text and username_text.strip():
                                        username = username_text.strip()
                            
                            # 提取评论内容 - Prioritized and refined
                            content = "未知内容"
                            content_selectors = [
                                "span.comment-content", # Specific span for comment text
                                "div.comment-text",     # Specific div for comment text
                                "p.content-text",       # Paragraph for comment text
                                "div.content",          # Generic content div
                                "span.text",            # Generic text span
                                "p.text",               # Generic text paragraph
                            ]
                            for content_selector in content_selectors:
                                content_el = await comment_element.query_selector(content_selector)
                                if content_el:
                                    content_text = await content_el.text_content()
                                    if content_text and content_text.strip(): # Ensure content is not just whitespace
                                        content = content_text.strip()
                                        break
                            
                            # 如果没有找到内容，可能内容就在评论元素本身 (with refinement)
                            if content == "未知内容" or len(content) < 2: # If content is too short or not found
                                full_text = await comment_element.text_content()
                                if full_text:
                                    full_text = full_text.strip()
                                    # Avoid using full_text if it's identical to username or too short
                                    if username != "未知用户" and username in full_text and len(full_text.replace(username, "").strip()) > 1:
                                        content = full_text.replace(username, "").strip()
                                    elif len(full_text) > 2 and full_text != username : # Only if it's meaningful
                                        content = full_text
                            
                            # 提取评论时间 - Prioritized and refined
                            time_location = "未知时间"
                            time_selectors = [
                                "span.time",            # Generic time span
                                "div.time",             # Generic time div
                                "span.date",            # Generic date span
                                "div.date",             # Generic date div
                                "time.publish-time",    # Semantic time tag with specific class
                                "span.publish-time",    # Span for publish time
                                "span[class*='time']",  # Any span with 'time' in its class
                            ]
                            for time_selector in time_selectors:
                                time_el = await comment_element.query_selector(time_selector)
                                if time_el:
                                    time_text = await time_el.text_content()
                                    if time_text and time_text.strip():
                                        time_location = time_text.strip()
                                        break
                            
                            # 如果内容有足够长度且找到用户名，添加评论
                            if username != "未知用户" and content != "未知内容" and len(content) > 2:
                                comments.append({
                                    "用户名": username,
                                    "内容": content,
                                    "时间": time_location
                                })
                        except Exception:
                            continue
                    
                    # 如果找到了评论，就不继续尝试其他选择器了
                    if comments:
                        break
            
            # 如果没有找到评论，尝试使用JavaScript提取评论
            if not comments:
                try:
                    js_comments = await self.browser.main_page.evaluate('''
                        () => {
                            const comments = [];
                            
                            // 尝试查找评论区域 - Mirroring Python's prioritized list
                            const commentContainers = document.querySelectorAll(
                                'div.comment-item, div.commentItem, .comment-root, div.normal-comment-item, div.sub-comment-item, div.comment-content-container, div.comment-wrapper, section.comment, div.feed-comment, div[class*="comment"]'
                            );
                            
                            for (const container of commentContainers) {
                                // 尝试获取用户名 - Mirroring Python's prioritized list
                                let username = "未知用户";
                                const usernameSelectors = ["a.user-name", "span.user-name", ".name", ".nick-name", ".nickname", "a[href*='/user/profile'] > span", "div.user-info a"];
                                for (const sel of usernameSelectors) {
                                    const usernameEl = container.querySelector(sel);
                                    if (usernameEl && usernameEl.textContent && usernameEl.textContent.trim()) {
                                        username = usernameEl.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // 尝试获取评论内容 - Mirroring Python's prioritized list
                                let content = "未知内容";
                                const contentSelectors = ["span.comment-content", "div.comment-text", "p.content-text", "div.content", "span.text", "p.text"];
                                for (const sel of contentSelectors) {
                                    const contentEl = container.querySelector(sel);
                                    if (contentEl && contentEl.textContent && contentEl.textContent.trim()) {
                                        content = contentEl.textContent.trim();
                                        break;
                                    }
                                }
                                
                                if (content === "未知内容" || content.length < 2) { // Fallback if specific content not found
                                    // 如果找不到明确的内容元素，尝试获取整个评论容器的文本
                                    const fullText = container.textContent.trim();
                                    if (username !== "未知用户" && fullText.includes(username)) {
                                        content = fullText.replace(username, "").trim();
                                    } else {
                                        content = fullText;
                                    }
                                }
                                
                                // 尝试获取时间 - Mirroring Python's prioritized list
                                let time = "未知时间";
                                const timeSelectors = ["span.time", "div.time", "span.date", "div.date", "time.publish-time", "span.publish-time", "span[class*='time']"];
                                for (const sel of timeSelectors) {
                                    const timeEl = container.querySelector(sel);
                                    if (timeEl && timeEl.textContent && timeEl.textContent.trim()) {
                                        time = timeEl.textContent.trim();
                                        break;
                                    }
                                }
                                
                                if (username !== "未知用户" && content !== "未知内容" && content.length > 2) {
                                    comments.push({
                                        username: username,
                                        content: content,
                                        time: time
                                    });
                                }
                            }
                            
                            return comments;
                        }
                    ''')
                    
                    if js_comments: # Check if js_comments is not None
                        # 将JavaScript结果添加到评论列表
                        for comment_data in js_comments:
                            comments.append({
                                "用户名": comment_data.get("username", "未知用户"),
                                "内容": comment_data.get("content", "未知内容"),
                                "时间": comment_data.get("time", "未知时间")
                            })
                except Exception as e:
                    # print(f"JS comment extraction failed: {e}") # Optional logging
                    pass
            
            # Fallback to user links: This is a very broad approach and should be a last resort.
            # It's kept for now but ideally, the above methods should capture comments.
            if not comments:
                try:
                    user_links = await self.browser.main_page.query_selector_all(
                        'div[class*="comment"] a[href*="/user/profile/"]' # Make user link search more contextual to comments
                    )
                    
                    for user_link in user_links:
                        try:
                            username_text_el = await user_link.query_selector("span, div") # Prefer text inside a span/div in the link
                            username = await (username_text_el.text_content() if username_text_el else user_link.text_content())
                            username = username.strip() if username else "未知用户"

                            if username == "未知用户" or not username: continue

                            # Try to find comment content near this user link
                            # This is heuristic and might need adjustment based on actual DOM
                            comment_container_candidate = await user_link.query_selector("xpath=ancestor::div[contains(@class, 'comment-item') or contains(@class, 'commentItem') or contains(@class, 'comment-wrapper')][1]")
                            
                            content = "未知内容"
                            if comment_container_candidate:
                                content_el = await comment_container_candidate.query_selector("span.comment-content, div.comment-text, p.content-text, div.content")
                                if content_el:
                                    content = (await content_el.text_content() or "").strip()
                                else: # Fallback to text_content of the container, excluding username
                                    full_container_text = (await comment_container_candidate.text_content() or "").strip()
                                    if username in full_container_text:
                                        content = full_container_text.replace(username, "").strip()
                                    else:
                                        content = full_container_text # Might be imperfect

                            if username and content and len(content) > 2:
                                comments.append({
                                    "用户名": username,
                                    "内容": content,
                                    "时间": "未知时间" # Time is hard to get reliably at this stage
                                })
                        except Exception:
                            continue
                except Exception as e:
                    # print(f"User link based comment extraction failed: {e}") # Optional logging
                    pass
            
            # 格式化返回结果
            if comments:
                result = f"共获取到 {len(comments)} 条评论：\n\n"
                for i, comment in enumerate(comments, 1):
                    result += f"{i}. {comment['用户名']}（{comment['时间']}）: {comment['内容']}\n\n"
                return result
            else:
                return "未找到任何评论，可能是帖子没有评论或评论区无法访问。"
        
        except Exception as e:
            return f"获取评论时出错: {str(e)}"
    
    async def analyze_note(self, url):
        """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
        
        Args:
            url (str): 笔记 URL
        
        Returns:
            dict: 分析结果
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return {"error": "请先登录小红书账号"}
        
        try:
            # 直接调用get_note_content获取笔记内容
            note_content_result = await self.get_note_content(url)
            
            # 检查是否获取成功
            if note_content_result.startswith("请先登录") or note_content_result.startswith("获取笔记内容时出错"):
                return {"error": note_content_result}
            
            # 解析获取到的笔记内容
            post_content = parse_note_content(note_content_result)
            
            # 检测笔记领域
            detected_domains = detect_domain(
                post_content.get("标题", ""), 
                post_content.get("内容", "")
            )
            
            # 提取关键词
            keywords = extract_keywords(
                f"{post_content.get('标题', '')} {post_content.get('内容', '')}"
            )
            
            # 返回分析结果
            return {
                "url": url,
                "标题": post_content.get("标题", "未知标题"),
                "作者": post_content.get("作者", "未知作者"),
                "内容": post_content.get("内容", "未能获取内容"),
                "领域": detected_domains,
                "关键词": keywords
            }
        
        except Exception as e:
            return {"error": f"分析笔记内容时出错: {str(e)}"}


# 添加同步封装函数，便于 main.py 中调用
def sync_get_note_content(url: str) -> str:
    """
    同步封装 NoteManager 的异步 get_note_content，确保 MCP 返回值为纯字符串，避免序列化异常
    """
    from src.infrastructure.browser.browser import BrowserManager
    browser_manager = BrowserManager()
    note_manager = NoteManager(browser_manager)
    loop = asyncio.get_event_loop()
    # 若已存在事件循环则复用，否则新建
    try:
        if loop.is_running():
            coro = note_manager.get_note_content(url)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result()
        else:
            result = loop.run_until_complete(note_manager.get_note_content(url))
        # 保证返回值为字符串
        if not isinstance(result, str):
            result = str(result)
        return result
    except Exception as e:
        return f"获取笔记内容时出错: {str(e)}"

def sync_get_note_comments(url: str) -> str:
    """
    同步封装 NoteManager 的异步 get_note_comments，确保 MCP 返回值为纯字符串，避免序列化异常
    """
    from src.infrastructure.browser.browser import BrowserManager
    browser_manager = BrowserManager()
    note_manager = NoteManager(browser_manager)
    loop = asyncio.get_event_loop()
    # 若已存在事件循环则复用，否则新建
    try:
        if loop.is_running():
            coro = note_manager.get_note_comments(url)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result()
        else:
            result = loop.run_until_complete(note_manager.get_note_comments(url))
        # 保证返回值为字符串
        if not isinstance(result, str):
            result = str(result)
        return result
    except Exception as e:
        return f"获取笔记评论时出错: {str(e)}"

def sync_analyze_note(url: str) -> dict:
    """
    同步封装 NoteManager 的异步 analyze_note，确保 MCP 返回值格式正确
    """
    from src.infrastructure.browser.browser import BrowserManager
    browser_manager = BrowserManager()
    note_manager = NoteManager(browser_manager)
    loop = asyncio.get_event_loop()
    # 若已存在事件循环则复用，否则新建
    try:
        if loop.is_running():
            coro = note_manager.analyze_note(url)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result()
        else:
            result = loop.run_until_complete(note_manager.analyze_note(url))
        # 确保返回值是字典
        if not isinstance(result, dict):
            result = {"error": "Result is not a dictionary"}
        return result
    except Exception as e:
        return {"error": f"分析笔记内容时出错: {str(e)}"}
