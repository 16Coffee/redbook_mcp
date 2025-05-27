"""
笔记相关功能模块，包括搜索、获取内容等
"""
import asyncio
import json
import re
from src.core.base.utils import extract_text, parse_note_content, detect_domain, extract_keywords
from src.core.logging.logger import logger


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

            from src.infrastructure.cache.cache import cache_manager

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

                                # 将带token的URL缓存起来，以便其他函数使用
                                # 缓存两种格式：完整URL和note_id->URL映射
                                await cache_manager.set(f"note_url:{note_id}", full_url, ttl=3600)  # 缓存1小时
                                logger.debug(f"已缓存笔记URL: {note_id} -> {full_url}")
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
        # 方法1: 使用footer内的标题元素
        title_element = await card.query_selector('div.footer a.title span')
        if title_element:
            title = await title_element.text_content()
            if title and title.strip():
                return title.strip()

        # 方法2: 直接获取标题元素
        title_element = await card.query_selector('a.title span')
        if title_element:
            title = await title_element.text_content()
            if title and title.strip():
                return title.strip()

        # 方法3: 获取任何可能的文本内容
        text_elements = await card.query_selector_all('span')
        potential_titles = []
        for text_el in text_elements:
            text = await text_el.text_content()
            if text and len(text.strip()) > 5:
                potential_titles.append(text.strip())

        if potential_titles:
            # 选择最长的文本作为标题
            return max(potential_titles, key=len)

        # 方法4: 使用JavaScript获取所有文本
        try:
            all_text = await card.evaluate('''
                el => Array.from(el.querySelectorAll("*"))
                    .map(node => node.textContent)
                    .filter(text => text && text.trim().length > 5)
            ''')

            if all_text and len(all_text) > 0:
                return max(all_text, key=len)
        except:
            pass

        # 如果所有方法都失败，返回默认标题
        return "未知标题"

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
            # 验证URL格式并进行必要的修正
            if not url:
                return "错误：请提供有效的笔记URL"

            # 检查URL是否包含xsec_token参数
            if 'xsec_token=' not in url:
                logger.warning(f"URL不包含xsec_token参数，尝试提取笔记ID并重构URL: {url}")

                import re

                # 尝试提取笔记ID（从explore/或者任何路径中）
                note_id_match = re.search(r'/([a-f0-9]{24})', url)
                if not note_id_match:
                    return "错误：无法从URL中提取笔记ID。请使用搜索功能获取的完整URL，确保包含xsec_token参数。"

                note_id = note_id_match.group(1)

                # 尝试从全局缓存中查找此ID对应的带token的URL
                from src.infrastructure.cache.cache import cache_manager
                cached_url = await cache_manager.get(f"note_url:{note_id}")

                if cached_url and 'xsec_token=' in cached_url:
                    logger.info(f"已从缓存中找到带token的URL: {cached_url}")
                    url = cached_url
                else:
                    # 无法自动获取token，返回错误提示
                    return "错误：笔记URL必须包含xsec_token参数。请先使用search_notes功能获取带token的完整URL。"

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
            await asyncio.sleep(3)

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
            # 验证URL格式并进行必要的修正
            if not url:
                return "错误：请提供有效的笔记URL"

            # 检查URL是否包含xsec_token参数
            if 'xsec_token=' not in url:
                logger.warning(f"get_note_comments: URL不包含xsec_token参数，尝试提取笔记ID并重构URL: {url}")

                import re

                # 尝试提取笔记ID（从explore/或者任何路径中）
                note_id_match = re.search(r'/([a-f0-9]{24})', url)
                if not note_id_match:
                    return "错误：无法从URL中提取笔记ID。请使用搜索功能获取的完整URL，确保包含xsec_token参数。"

                note_id = note_id_match.group(1)

                # 尝试从全局缓存中查找此ID对应的带token的URL
                from src.infrastructure.cache.cache import cache_manager
                cached_url = await cache_manager.get(f"note_url:{note_id}")

                if cached_url and 'xsec_token=' in cached_url:
                    logger.info(f"已从缓存中找到带token的URL: {cached_url}")
                    url = cached_url
                else:
                    # 无法自动获取token，返回错误提示
                    return "错误：笔记URL必须包含xsec_token参数。请先使用search_notes功能获取带token的完整URL。"

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
                        # 使用JavaScript滚动到元素（仅滚动，不点击）
                        await self.browser.main_page.evaluate('''
                            (element) => {
                                element.scrollIntoView({ behavior: "smooth", block: "center" });
                            }
                        ''', comment_section)

                        await asyncio.sleep(2)

                        # 移除点击操作 - 仅获取评论不需要激活评论输入框
                        # 注释掉原来的点击代码，避免意外触发评论输入框
                        # try:
                        #     await comment_section.click()
                        #     await asyncio.sleep(2)
                        # except Exception:
                        #     pass

                        break
                except Exception:
                    continue

            # 滚动页面以加载更多评论
            for i in range(8):
                try:
                    await self.browser.main_page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)

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
                                await more_btn.click()
                                await asyncio.sleep(2)
                        except Exception:
                            continue
                except Exception:
                    pass

            # 获取评论
            comments = []

            # 使用特定评论选择器
            comment_selectors = [
                "div.comment-item",
                "div.commentItem",
                "div.comment-content",
                "div.comment-wrapper",
                "section.comment",
                "div.feed-comment"
            ]

            for selector in comment_selectors:
                comment_elements = await self.browser.main_page.query_selector_all(selector)
                if comment_elements and len(comment_elements) > 0:
                    for comment_element in comment_elements:
                        try:
                            # 提取评论者名称
                            username = "未知用户"
                            username_selectors = ["span.user-name", "a.name", "div.username", "span.nickname", "a.user-nickname"]
                            for username_selector in username_selectors:
                                username_el = await comment_element.query_selector(username_selector)
                                if username_el:
                                    username_text = await username_el.text_content()
                                    username = username_text.strip()
                                    break

                            # 如果没有找到，尝试通过用户链接查找
                            if username == "未知用户":
                                user_link = await comment_element.query_selector('a[href*="/user/profile/"]')
                                if user_link:
                                    username_text = await user_link.text_content()
                                    username = username_text.strip()

                            # 提取评论内容
                            content = "未知内容"
                            content_selectors = ["div.content", "p.content", "div.text", "span.content", "div.comment-text"]
                            for content_selector in content_selectors:
                                content_el = await comment_element.query_selector(content_selector)
                                if content_el:
                                    content_text = await content_el.text_content()
                                    content = content_text.strip()
                                    break

                            # 如果没有找到内容，可能内容就在评论元素本身
                            if content == "未知内容":
                                full_text = await comment_element.text_content()
                                if username != "未知用户" and username in full_text:
                                    content = full_text.replace(username, "").strip()
                                else:
                                    content = full_text.strip()

                            # 提取评论时间
                            time_location = "未知时间"
                            time_selectors = ["span.time", "div.time", "span.date", "div.date", "time"]
                            for time_selector in time_selectors:
                                time_el = await comment_element.query_selector(time_selector)
                                if time_el:
                                    time_text = await time_el.text_content()
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

                            // 尝试查找评论区域
                            const commentContainers = document.querySelectorAll(
                                '.comment-item, .commentItem, .comment-content, .comment-wrapper, section.comment, .feed-comment'
                            );

                            for (const container of commentContainers) {
                                // 尝试获取用户名
                                let username = "未知用户";
                                const usernameEl = container.querySelector('.user-nickname, .nickname, .user-name, a.name, .username');
                                if (usernameEl) {
                                    username = usernameEl.textContent.trim();
                                }

                                // 尝试获取评论内容
                                let content = "未知内容";
                                const contentEl = container.querySelector('.content, .text, .comment-text');
                                if (contentEl) {
                                    content = contentEl.textContent.trim();
                                } else {
                                    // 如果找不到明确的内容元素，尝试获取整个评论容器的文本
                                    const fullText = container.textContent.trim();
                                    if (username !== "未知用户" && fullText.includes(username)) {
                                        content = fullText.replace(username, "").trim();
                                    } else {
                                        content = fullText;
                                    }
                                }

                                // 尝试获取时间
                                let time = "未知时间";
                                const timeEl = container.querySelector('.time, .date, time');
                                if (timeEl) {
                                    time = timeEl.textContent.trim();
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

                    # 将JavaScript结果添加到评论列表
                    for comment in js_comments:
                        comments.append({
                            "用户名": comment.get("username", "未知用户"),
                            "内容": comment.get("content", "未知内容"),
                            "时间": comment.get("time", "未知时间")
                        })
                except Exception:
                    pass

            # 如果还是没有找到评论，尝试通过用户链接方式查找
            if not comments:
                try:
                    # 获取所有用户名元素
                    user_links = await self.browser.main_page.query_selector_all('a[href*="/user/profile/"]')

                    for user_link in user_links:
                        try:
                            username = await user_link.text_content()
                            username = username.strip()

                            # 尝试获取评论内容
                            content = await self.browser.main_page.evaluate('''
                                (usernameElement) => {
                                    const parent = usernameElement.parentElement;
                                    if (!parent) return null;

                                    // 尝试获取同级的下一个元素
                                    let sibling = usernameElement.nextElementSibling;
                                    while (sibling) {
                                        const text = sibling.textContent.trim();
                                        if (text) return text;
                                        sibling = sibling.nextElementSibling;
                                    }

                                    // 尝试获取父元素的文本，并过滤掉用户名
                                    const allText = parent.textContent.trim();
                                    if (allText && allText.includes(usernameElement.textContent.trim())) {
                                        return allText.replace(usernameElement.textContent.trim(), '').trim();
                                    }

                                    return null;
                                }
                            ''', user_link)

                            if username and content:
                                comments.append({
                                    "用户名": username,
                                    "内容": content,
                                    "时间": "未知时间"
                                })
                        except Exception:
                            continue
                except Exception:
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
            dict: 包含分析结果的字典
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return {"error": "请先登录小红书账号"}

        try:
            # 验证URL格式并进行必要的修正
            if not url:
                return {"error": "请提供有效的笔记URL"}

            # 检查URL是否包含xsec_token参数
            if 'xsec_token=' not in url:
                logger.warning(f"analyze_note: URL不包含xsec_token参数，尝试提取笔记ID并重构URL: {url}")

                import re

                # 尝试提取笔记ID（从explore/或者任何路径中）
                note_id_match = re.search(r'/([a-f0-9]{24})', url)
                if not note_id_match:
                    return {"error": "无法从URL中提取笔记ID。请使用搜索功能获取的完整URL，确保包含xsec_token参数。"}

                note_id = note_id_match.group(1)

                # 尝试从全局缓存中查找此ID对应的带token的URL
                from src.infrastructure.cache.cache import cache_manager
                cached_url = await cache_manager.get(f"note_url:{note_id}")

                if cached_url and 'xsec_token=' in cached_url:
                    logger.info(f"已从缓存中找到带token的URL: {cached_url}")
                    url = cached_url
                else:
                    # 无法自动获取token，返回错误提示
                    return {"error": "笔记URL必须包含xsec_token参数。请先使用search_notes功能获取带token的完整URL。"}

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
            await asyncio.sleep(3)

            # 获取页面文本内容
            page_text = await self.browser.main_page.evaluate('() => document.body.innerText')

            # 提取笔记信息
            note_info = await self.browser.main_page.evaluate('''
                () => {
                    // 尝试获取标题
                    let title = "";
                    const titleSelectors = ['#detail-title', 'div.title', 'h1', '.note-content .title'];
                    for (const selector of titleSelectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent.trim()) {
                            title = el.textContent.trim();
                            break;
                        }
                    }

                    // 尝试获取作者
                    let author = "";
                    const authorSelectors = ['.user-nickname', '.author-nickname', '.nickname', 'span.username'];
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

                    // 提取话题标签
                    const topics = [];
                    const topicSelectors = ['.tag-item', '.topic-item', '.hash-tag'];
                    for (const selector of topicSelectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el && el.textContent.trim()) {
                                topics.push(el.textContent.trim());
                            }
                        });
                    }

                    return {
                        title: title || "未知标题",
                        author: author || "未知作者",
                        content: content || "未能获取内容",
                        topics: topics
                    };
                }
            ''')

            # 提取图片
            images = await self._extract_images()

            # 构造结果
            result = {
                "标题": note_info['title'],
                "作者": note_info['author'],
                "内容": note_info['content'],
                "话题标签": note_info['topics'],
                "图片数量": len(images),
                "页面文本概要": page_text[:500] + "..." if len(page_text) > 500 else page_text,
                "URL": url
            }

            return result

        except Exception as e:
            return {"error": f"分析笔记时出错: {str(e)}"}


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
