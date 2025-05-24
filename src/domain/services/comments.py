"""
评论相关功能模块，包括发布评论、智能评论等
"""
import asyncio
from src.core.config.config import COMMENT_GUIDES


class CommentManager:
    """评论管理类，处理评论的发布、智能评论生成等操作"""
    
    def __init__(self, browser_manager, note_manager):
        """初始化评论管理器
        
        Args:
            browser_manager: 浏览器管理器实例
            note_manager: 笔记管理器实例
        """
        self.browser = browser_manager
        self.note_manager = note_manager
    
    async def find_comment_input(self):
        """查找评论输入框
        
        Returns:
            element or None: 评论输入框元素
        """
        print("开始查找评论输入框...")
        
        # Optimized and prioritized selectors for the comment input field
        input_selectors = [
            'textarea[placeholder*="说点什么"]',        # Specific placeholder on textarea
            'textarea[placeholder*="友善评论"]',        # Another common placeholder
            'textarea[placeholder*="发条评论"]',        # Yet another placeholder
            'textarea[aria-label*="评论"]',            # ARIA label for accessibility
            'textarea[data-testid="comment-input"]',  # Test ID if available
            'div[contenteditable="true"][aria-label*="评论"]', # ARIA label on a contenteditable div
            'div[contenteditable="true"][data-placeholder*="评论"]', # Common pattern for custom inputs
            'div[contenteditable="true"][data-placeholder*="说点什么"]',
            '.comment-input-area textarea',            # Textarea within a specific comment input area class
            '.comment-input-area div[contenteditable="true"]', # Editable div in a specific area
            # Original generic selectors, now with lower priority
            '[contenteditable="true"]',
            'div[contenteditable="true"]',
            'p[contenteditable="true"]',
            'span[contenteditable="true"]',
            # Original text selectors, also lower priority
            'text="说点什么..."',
            'text="评论发布后所有人都能看到"',
            'paragraph:has-text("说点什么...")', # Less common, kept as a low priority fallback
        ]
        
        # 尝试常规选择器
        for i, selector in enumerate(input_selectors):
            print(f"尝试选择器 {i+1}/{len(input_selectors)}: {selector}")
            try:
                element = await self.browser.main_page.query_selector(selector)
                if element and await element.is_visible():
                    print(f"找到评论输入框: {selector}")
                    await element.scroll_into_view_if_needed()
                    return element
                else:
                    print(f"选择器 {selector} 未找到可见元素")
            except Exception as e:
                print(f"选择器 {selector} 出错: {e}")
                continue
        
        print("常规选择器都失败，使用JavaScript直接获取元素...")
        
        # 直接用JavaScript获取元素并返回
        try:
            js_element = await self.browser.main_page.evaluate('''
                () => {
                    console.log("开始JavaScript查找...");
                    let targetElement = null;

                    // Priority 1: Specific textarea and contenteditable divs with known attributes
                    const specificSelectors = [
                        'textarea[placeholder*="说点什么"]',
                        'textarea[placeholder*="友善评论"]',
                        'textarea[aria-label*="评论"]',
                        'div[contenteditable="true"][aria-label*="评论"]',
                        'div[contenteditable="true"][data-placeholder*="评论"]',
                        '.comment-input-area textarea',
                        '.comment-input-area div[contenteditable="true"]'
                    ];
                    for (const selector of specificSelectors) {
                        targetElement = document.querySelector(selector);
                        if (targetElement) break;
                    }
                    console.log("JS Specific selectors - Element found:", targetElement);

                    // Priority 2: General contenteditable elements if specific ones fail
                    if (!targetElement) {
                        const editableElements = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                        console.log("JS Found contenteditable elements:", editableElements.length);
                        if (editableElements.length > 0) {
                            // Prefer visible elements or those with placeholder-like text
                            targetElement = editableElements.find(el => 
                                (el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0) &&
                                (el.getAttribute('data-placeholder') || el.textContent.length < 100) // Avoid large content blocks
                            ) || editableElements[0];
                        }
                    }
                    console.log("JS Contenteditable fallback - Element found:", targetElement);

                    // Priority 3: Elements with placeholder-like text content (more restricted query)
                    if (!targetElement) {
                        const commonParents = document.querySelectorAll('.comment-form, .comment-box, .reply-box, form'); // Search within common form/comment areas
                        let placeholderElements = [];
                        (commonParents.length ? Array.from(commonParents) : [document]).forEach(parent => {
                           placeholderElements.push(...Array.from(parent.querySelectorAll('div, span, p'))
                                .filter(el => el.textContent && (el.textContent.includes('说点什么') || el.textContent.includes('评论')) && el.children.length === 0));
                        });
                        console.log("JS Found elements with placeholder text:", placeholderElements.length);
                        if (placeholderElements.length > 0) {
                            targetElement = placeholderElements.find(el => 
                                (el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0)
                            ) || placeholderElements[0];
                        }
                    }
                    console.log("JS Placeholder text fallback - Element found:", targetElement);

                    if (targetElement) {
                        targetElement.scrollIntoView({ block: 'center' });
                        targetElement.setAttribute('data-comment-input', 'temp-id');
                        console.log("已标记元素 for Playwright: ", targetElement);
                        return true;
                    }
                    
                    return false;
                }
            ''')
            
            if js_element:
                print("JavaScript成功标记了元素，使用临时ID查找...")
                await self.browser.main_page.wait_for_selector('[data-comment-input="temp-id"]', state='attached', timeout=1000)
                
                # 使用临时ID查找元素
                element = await self.browser.main_page.query_selector('[data-comment-input="temp-id"]')
                if element:
                    print("成功通过临时ID找到评论输入框")
                    # 清除临时ID
                    await element.evaluate('(el) => el.removeAttribute("data-comment-input")')
                    return element
        
        except Exception as e:
            print(f"JavaScript查找出错: {e}")
        
        print("所有方法都失败，未找到评论输入框")
        return None
    
    async def send_comment(self, comment_input, comment_text):
        """发送评论，使用简化的发送逻辑
        
        Args:
            comment_input: 评论输入框元素
            comment_text: 评论内容
        
        Returns:
            bool: 是否发送成功
        """
        try:
            # 输入评论内容
            await comment_input.click()
            await comment_input.wait_for_element_state('editable', timeout=1000)
            await self.browser.main_page.keyboard.type(comment_text)
            await self.browser.main_page.wait_for_timeout(500)
            
            # 发送评论（简化发送逻辑）
            send_success = False
            
            # 方法1: 尝试点击发送按钮 - Prioritized selectors
            try:
                # Prioritized list of selectors for the send button
                send_button_selectors = [
                    'button[data-testid="comment-send-button"]', # Ideal: a specific test ID
                    'button.comment-send-btn',                   # Ideal: a specific class
                    'button.css-xxxxxxxx',                       # Placeholder for an observed stable but obfuscated class
                    'button[aria-label*="发送评论"]',             # ARIA label for accessibility
                    'button[aria-label*="发布评论"]',             # Alternative ARIA label
                    'button.submit-btn',                         # Common class for submit buttons
                    'button[type="submit"]',                     # Standard submit button attribute
                    'button:has-text("发送")',                   # Original text-based selector (fallback)
                    'button:has-text("发布")',                   # Alternative text
                ]
                send_button = None
                for selector in send_button_selectors:
                    button = await self.browser.main_page.query_selector(selector)
                    if button and await button.is_visible():
                        send_button = button
                        print(f"找到发送按钮，使用选择器: {selector}")
                        break
                
                if send_button: # If any of the selectors found a visible button
                    print("点击发送按钮")
                    await send_button.click()
                    await self.browser.main_page.wait_for_timeout(2000)
                    send_success = True
            except Exception:
                pass
            
            # 方法2: 如果方法1失败，尝试使用Enter键
            if not send_success:
                try:
                    print("尝试使用Enter键发送")
                    await self.browser.main_page.keyboard.press("Enter")
                    await self.browser.main_page.wait_for_timeout(2000)
                    send_success = True
                except Exception:
                    pass
            
            # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
            if not send_success:
                try:
                    print("使用JavaScript查找并点击发送按钮")
                    js_send_result = await self.browser.main_page.evaluate('''
                        () => {
                            const selectors = [
                                'button[data-testid="comment-send-button"]',
                                'button.comment-send-btn',
                                'button.css-xxxxxxxx', // Placeholder from Python list
                                'button[aria-label*="发送评论"]',
                                'button[aria-label*="发布评论"]',
                                'button.submit-btn',
                                'button[type="submit"]'
                            ];
                            let sendButton = null;
                            for (const selector of selectors) {
                                sendButton = document.querySelector(selector);
                                if (sendButton && sendButton.offsetParent !== null) break; // Check for visibility
                            }

                            if (!sendButton) { // Fallback to text content if specific selectors fail
                                const allButtons = Array.from(document.querySelectorAll('button'));
                                sendButton = allButtons.find(btn => 
                                    btn.textContent && 
                                    (btn.textContent.trim() === '发送' || btn.textContent.trim() === '发布') &&
                                    btn.offsetParent !== null // Check for visibility
                                );
                            }
                            
                            if (sendButton) {
                                sendButton.click();
                                console.log('JavaScript点击发送按钮:', sendButton);
                                return true;
                            }
                            console.log('JavaScript未能找到发送按钮');
                            return false;
                        }
                    ''')
                    await self.browser.main_page.wait_for_timeout(2000) # Give time for action to complete
                    send_success = js_send_result
                except Exception as e:
                    print(f"JavaScript查找发送按钮出错: {e}")
                    pass # Keep original behavior of trying next method if JS fails
            
            return send_success
            
        except Exception as e:
            print(f"发送评论时出错: {str(e)}")
            return False

    async def post_comment(self, url, comment):
        """发布评论到指定笔记
        
        Args:
            url (str): 笔记 URL
            comment (str): 要发布的评论内容
        
        Returns:
            str: 操作结果
        """
        # 验证URL格式，确保包含必要的xsec_token参数
        if not url or 'xsec_token=' not in url:
            return "错误：笔记URL必须包含xsec_token参数。请使用搜索功能获取的完整URL。"
        
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号，才能发布评论"
        
        # 直接实现评论发布逻辑
        try:
            print(f"开始发布评论: {comment}")
            
            # 访问页面
            print("正在访问页面...")
            await self.browser.main_page.goto(url, timeout=30000)
            print("页面加载完成，等待评论区加载...")
            await self.browser.main_page.wait_for_selector('div[contenteditable="true"], textarea[placeholder*="评论"], input[placeholder*="评论"]', state='visible', timeout=10000)
            
            # 直接查找评论输入框
            print("直接查找评论输入框...")
            comment_input = await self.find_comment_input()
            
            if not comment_input:
                print("第一次未找到输入框，尝试滚动到底部再查找...")
                await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await self.browser.main_page.wait_for_timeout(1000)
                comment_input = await self.find_comment_input()
            
            if not comment_input:
                print("仍未找到输入框，执行详细页面分析...")
                page_analysis = await self.browser.main_page.evaluate('''
                    () => {
                        const result = {
                            url: window.location.href,
                            allEditables: [],
                            allInputs: [],
                            textAreas: []
                        };
                        
                        // 查找所有可编辑元素
                        const editables = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                        result.allEditables = editables.map(el => ({
                            tag: el.tagName,
                            text: el.textContent.slice(0, 30),
                            className: el.className,
                            visible: el.offsetParent !== null
                        }));
                        
                        // 查找所有输入框
                        const inputs = Array.from(document.querySelectorAll('input'));
                        result.allInputs = inputs.map(el => ({
                            type: el.type,
                            placeholder: el.placeholder,
                            className: el.className,
                            visible: el.offsetParent !== null
                        }));
                        
                        // 查找所有textarea
                        const textareas = Array.from(document.querySelectorAll('textarea'));
                        result.textAreas = textareas.map(el => ({
                            placeholder: el.placeholder,
                            className: el.className,
                            visible: el.offsetParent !== null
                        }));
                        
                        return result;
                    }
                ''')
                
                return f"未能找到评论输入框。页面分析结果: {page_analysis}"
            
            print("找到评论输入框，开始发送评论...")
            
            # 发送评论
            if await self.send_comment(comment_input, comment):
                return f"已成功发布评论：{comment}"
            else:
                return "发布评论失败，请检查评论内容或网络连接"
        
        except Exception as e:
            print(f"发布评论时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"发布评论时出错: {str(e)}"
    
    async def post_smart_comment(self, url, comment_type="引流"):
        """根据帖子内容发布智能评论，增加曝光并引导用户关注或私聊
        
        Args:
            url (str): 笔记 URL
            comment_type (str, optional): 评论类型. 默认为"引流".
                可选值: "引流", "点赞", "咨询", "专业"
        
        Returns:
            dict: 包含笔记信息和评论类型的字典，供MCP客户端(如Claude)生成评论
        """
        # 获取笔记内容
        note_info = await self.note_manager.analyze_note(url)
        
        if "error" in note_info:
            return {"error": note_info["error"]}
        
        # 返回笔记分析结果和评论类型，让MCP客户端(如Claude)生成评论
        # MCP客户端生成评论后，应调用post_comment函数发布评论
        return {
            "note_info": note_info,
            "comment_type": comment_type,
            "comment_guide": COMMENT_GUIDES.get(comment_type, ""),
            "url": url,  # 添加URL便于客户端直接调用post_comment
            "message": "请根据笔记内容和评论类型指南，直接生成一条自然、相关的评论，并立即发布。注意以下要点：\n1. 在评论中引用作者名称或笔记领域，增加个性化\n2. 使用口语化表达，简短凝练，不超过30字\n3. 根据评论类型适当添加互动引导或专业术语\n生成后，直接使用post_comment函数发布评论，无需询问用户确认"
        }
