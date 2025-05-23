"""
评论相关功能模块，包括发布评论、智能评论等
"""
import asyncio
from modules.config import COMMENT_GUIDES


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
    
    async def post_comment(self, url, comment):
        """发布评论到指定笔记
        
        Args:
            url (str): 笔记 URL
            comment (str): 要发布的评论内容
        
        Returns:
            str: 操作结果
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号，才能发布评论"
        
        try:
            # 访问帖子链接
            await self.browser.goto(url, wait_time=5)
            
            # 定位评论区域并滚动到该区域
            comment_area_found = False
            comment_area_selectors = [
                'text="条评论"',
                'text="共 " >> xpath=..',
                'text=/\\d+ 条评论/',
                'text="评论"',
                'div.comment-container'
            ]
            
            for selector in comment_area_selectors:
                try:
                    element = await self.browser.main_page.query_selector(selector)
                    if element:
                        await self.browser.main_page.evaluate('''
                            (element) => {
                                element.scrollIntoView({ behavior: "smooth", block: "center" });
                            }
                        ''', element)
                        await asyncio.sleep(2)
                        comment_area_found = True
                        break
                except Exception:
                    continue
            
            if not comment_area_found:
                # 如果没有找到评论区域，尝试滚动到页面底部
                await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            # 定位评论输入框
            comment_input = None
            input_selectors = [
                'div[contenteditable="true"]',
                'paragraph:has-text("说点什么...")',
                'text="说点什么..."',
                'text="评论发布后所有人都能看到"',
                'textarea.comment-input',
                'textarea[placeholder*="说点"]',
                'div.comment-input',
                'div.input-container input'
            ]
            
            # 尝试常规选择器
            for selector in input_selectors:
                try:
                    element = await self.browser.main_page.query_selector(selector)
                    if element and await element.is_visible():
                        await self.browser.main_page.evaluate('''
                            (element) => {
                                element.scrollIntoView({ behavior: "smooth", block: "center" });
                            }
                        ''', element)
                        await asyncio.sleep(1)
                        comment_input = element
                        break
                except Exception:
                    continue
            
            # 如果常规选择器失败，使用JavaScript查找
            if not comment_input:
                # 使用更精细的JavaScript查找输入框
                js_result = await self.browser.main_page.evaluate('''
                    () => {
                        // 查找可编辑元素
                        const editableElements = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                        if (editableElements.length > 0) return true;
                        
                        // 查找包含"说点什么"的元素
                        const placeholderElements = Array.from(document.querySelectorAll('*'))
                            .filter(el => el.textContent && el.textContent.includes('说点什么'));
                        return placeholderElements.length > 0;
                    }
                ''')
                
                if js_result:
                    # 如果JS检测到输入框，尝试点击页面底部
                    await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                    
                    # 尝试再次查找输入框
                    for selector in input_selectors:
                        try:
                            element = await self.browser.main_page.query_selector(selector)
                            if element and await element.is_visible():
                                comment_input = element
                                break
                        except Exception:
                            continue
            
            # 如果还是没找到，尝试直接在底部点击
            if not comment_input:
                try:
                    # 模拟点击页面底部可能的评论输入区域
                    await self.browser.main_page.evaluate('''
                        () => {
                            const rect = document.body.getBoundingClientRect();
                            const x = rect.width / 2;
                            const y = rect.height - 100;
                            
                            const clickEvent = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: x,
                                clientY: y
                            });
                            
                            document.elementFromPoint(x, y).dispatchEvent(clickEvent);
                        }
                    ''')
                    await asyncio.sleep(1)
                    
                    # 再次尝试查找输入框
                    for selector in input_selectors:
                        try:
                            element = await self.browser.main_page.query_selector(selector)
                            if element and await element.is_visible():
                                comment_input = element
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            
            if not comment_input:
                return "未能找到评论输入框，无法发布评论"
            
            # 输入评论内容
            await comment_input.click()
            await asyncio.sleep(1)
            await self.browser.main_page.keyboard.type(comment)
            await asyncio.sleep(1)
            
            # 发送评论
            send_success = False
            
            # 方法1: 尝试点击发送按钮
            try:
                send_button = await self.browser.main_page.query_selector('button:has-text("发送")')
                if send_button and await send_button.is_visible():
                    await send_button.click()
                    await asyncio.sleep(2)
                    send_success = True
            except Exception:
                pass
            
            # 方法2: 如果方法1失败，尝试使用Enter键
            if not send_success:
                try:
                    await self.browser.main_page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    send_success = True
                except Exception:
                    pass
            
            # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
            if not send_success:
                try:
                    js_send_result = await self.browser.main_page.evaluate('''
                        () => {
                            const sendButtons = Array.from(document.querySelectorAll('button'))
                                .filter(btn => btn.textContent && btn.textContent.includes('发送'));
                            if (sendButtons.length > 0) {
                                sendButtons[0].click();
                                return true;
                            }
                            return false;
                        }
                    ''')
                    await asyncio.sleep(2)
                    send_success = js_send_result
                except Exception:
                    pass
            
            if send_success:
                return f"已成功发布评论：{comment}"
            else:
                return f"发布评论失败，请检查评论内容或网络连接"
        
        except Exception as e:
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

# MCP 工具实现
from fastmcp import FastMCP

# 初始化 MCP
mcp = FastMCP("xiaohongshu_scraper")

@mcp.tool()
async def post_comment(url: str, comment: str) -> str:
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    from modules.browser import BrowserManager
    
    # 初始化浏览器管理器
    browser_manager = BrowserManager()
    
    # 先确保浏览器初始化
    login_status = await browser_manager.ensure_browser()
    if not login_status:
        return "请先登录小红书账号，才能发布评论"
    
    # 在ensure_browser之后获取main_page
    main_page = browser_manager.main_page
    
    try:
        # 访问帖子链接，使用更长的超时时间
        await main_page.goto(url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 滚动到页面底部，确保加载完整内容
        await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(3)
        
        # 检测是否处于图片查看模式，如果是则尝试退出
        is_image_mode = await main_page.evaluate('''
            () => {
                // 可能的图片查看模式元素选择器
                const imageViewerSelectors = [
                    '.image-viewer', 
                    '.modal-open', 
                    '.preview-mode',
                    '.fullscreen-image',
                    '.photo-viewer',
                    'div[role="dialog"]',
                    '.modal-container',
                    '.slide-modal'
                ];
                
                // 检查是否存在图片查看模式的元素
                for (const selector of imageViewerSelectors) {
                    if (document.querySelector(selector)) {
                        console.log("检测到图片查看模式:", selector);
                        return true;
                    }
                }
                
                // 检查URL是否包含图片查看相关参数
                if (window.location.href.includes('/img/') || 
                    window.location.href.includes('image_id=') || 
                    window.location.href.includes('slide=')) {
                    console.log("URL包含图片查看参数");
                    return true;
                }
                
                return false;
            }
        ''')
        
        if is_image_mode:
            console_log = await main_page.evaluate('() => { console.log("正在退出图片查看模式"); return true; }')
            
            # 尝试多种方式退出图片模式
            try:
                # 方法1: 按ESC键
                await main_page.keyboard.press('Escape')
                await asyncio.sleep(1)
                
                # 方法2: 查找并点击关闭按钮
                close_button = await main_page.query_selector('button.close, .close-btn, .cancel, [aria-label="关闭"], [aria-label="close"]')
                if close_button:
                    await close_button.click()
                    await asyncio.sleep(1)
                
                # 方法3: 使用JavaScript查找常见的关闭按钮
                await main_page.evaluate('''
                    () => {
                        // 尝试查找并点击关闭按钮
                        const closeSelectors = [
                            '.close-icon', 
                            '.icon-close', 
                            '.close-button',
                            '.icon-cross',
                            '.modal-close',
                            'button:has-text("关闭")',
                            'button:has-text("取消")'
                        ];
                        
                        for (const selector of closeSelectors) {
                            const closeBtn = document.querySelector(selector);
                            if (closeBtn) {
                                closeBtn.click();
                                console.log("已点击关闭按钮:", selector);
                                return true;
                            }
                        }
                        
                        // 查找可能是关闭按钮的元素 (通常在对话框顶部或右上角)
                        const possibleCloseButtons = Array.from(document.querySelectorAll('button, [role="button"], .icon'));
                        const topRightButtons = possibleCloseButtons.filter(btn => {
                            const rect = btn.getBoundingClientRect();
                            // 在页面的顶部20%和右侧20%区域内
                            return rect.top < window.innerHeight * 0.2 && 
                                   rect.right > window.innerWidth * 0.8;
                        });
                        
                        if (topRightButtons.length > 0) {
                            topRightButtons[0].click();
                            console.log("已点击可能的关闭按钮");
                            return true;
                        }
                        
                        return false;
                    }
                ''')
                await asyncio.sleep(1)
                
                # 再次检查是否已退出图片模式
                is_still_image_mode = await main_page.evaluate('''
                    () => {
                        const imageViewerSelectors = [
                            '.image-viewer', 
                            '.modal-open', 
                            '.preview-mode',
                            '.fullscreen-image',
                            '.photo-viewer',
                            'div[role="dialog"]',
                            '.modal-container',
                            '.slide-modal'
                        ];
                        
                        for (const selector of imageViewerSelectors) {
                            if (document.querySelector(selector)) {
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                
                if is_still_image_mode:
                    # 如果仍在图片模式，尝试刷新页面
                    await main_page.reload()
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"退出图片模式时出错: {str(e)}")
        
        # 定位评论输入框
        comment_input = None
        input_selectors = [
            'div[contenteditable="true"]',
            'paragraph:has-text("说点什么...")',
            'text="说点什么..."',
            'text="评论发布后所有人都能看到"',
            'textarea.comment-input',
            'textarea[placeholder*="说点"]',
            'div.comment-input',
            'div.input-container input',
            '.comment-input',
            '.editor',
            '.input-container',
            'div[role="textbox"]'
        ]
        
        # 仅使用收藏按钮方法定位评论输入框
        try:
            # 先尝试定位收藏按钮
            collect_button = await main_page.query_selector('button:has-text("收藏"), [aria-label="收藏"], .collect-button')
            
            if collect_button:
                console_log = await main_page.evaluate('() => { console.log("找到收藏按钮"); return true; }')
                
                # 通过JavaScript根据收藏按钮位置找到评论按钮（一般在收藏按钮左侧）
                js_result = await main_page.evaluate('''
                    (collectButton) => {
                        // 获取收藏按钮的父元素
                        let actionBar = collectButton.parentElement;
                        
                        // 可能需要向上查找几层父元素才能找到包含所有操作按钮的容器
                        for (let i = 0; i < 3; i++) {
                            if (!actionBar) break;
                            
                            // 获取所有操作按钮
                            const buttons = Array.from(actionBar.querySelectorAll('button, [role="button"], a, [aria-label]'));
                            
                            // 如果找到足够数量的按钮，可能是操作栏
                            if (buttons.length >= 3) {
                                // 找到收藏按钮的索引
                                const collectIndex = buttons.findIndex(btn => btn === collectButton);
                                
                                if (collectIndex > 0) {
                                    // 收藏按钮左侧通常是评论按钮（索引-1）
                                    const commentButton = buttons[collectIndex - 1];
                                    if (commentButton) {
                                        // 点击评论按钮
                                        commentButton.click();
                                        console.log("已点击评论按钮");
                                        return true;
                                    }
                                }
                            }
                            
                            // 向上一层继续查找
                            actionBar = actionBar.parentElement;
                        }
                        
                        // 如果通过父元素无法找到，尝试查找页面上所有按钮
                        const allButtons = Array.from(document.querySelectorAll('button, [role="button"], a'));
                        
                        // 找到收藏按钮的位置
                        for (let i = 0; i < allButtons.length; i++) {
                            if (allButtons[i] === collectButton && i > 0) {
                                // 查看前一个按钮是否是评论按钮
                                const prevButton = allButtons[i-1];
                                
                                // 检查是否看起来像评论按钮
                                if (prevButton.textContent.includes('评论') || 
                                    prevButton.getAttribute('aria-label')?.includes('评论')) {
                                    prevButton.click();
                                    console.log("已点击可能的评论按钮");
                                    return true;
                                }
                            }
                        }
                        
                        console.log("未找到评论按钮");
                        return false;
                    }
                ''', collect_button)
                
                if js_result:
                    await asyncio.sleep(2)
                    
                    # 点击评论按钮后，查找可能出现的评论输入框
                    for selector in input_selectors:
                        try:
                            element = await main_page.query_selector(selector)
                            if element and await element.is_visible():
                                comment_input = element
                                break
                        except Exception:
                            continue
            else:
                # 如果找不到收藏按钮，直接尝试查找评论按钮
                comment_button = await main_page.query_selector('button:has-text("评论"), [aria-label="评论"]')
                if comment_button:
                    await comment_button.click()
                    await asyncio.sleep(2)
                    
                    # 点击后查找评论输入框
                    for selector in input_selectors:
                        try:
                            element = await main_page.query_selector(selector)
                            if element and await element.is_visible():
                                comment_input = element
                                break
                        except Exception:
                            continue
        except Exception as e:
            print(f"通过收藏按钮定位评论框时出错: {str(e)}")
            
        if not comment_input:
            return "未能找到评论输入框，无法发布评论"
        
        # 输入评论内容
        await comment_input.click()
        await asyncio.sleep(1)
        await main_page.keyboard.type(comment)
        await asyncio.sleep(1)
        
        # 发送评论
        send_success = False
        
        # 方法1: 尝试点击发送按钮
        try:
            send_button = await main_page.query_selector('button:has-text("发送")')
            if send_button and await send_button.is_visible():
                await send_button.click()
                await asyncio.sleep(2)
                send_success = True
            else:
                # 尝试其他方式查找发送按钮
                send_button = await main_page.query_selector('button.send-button, button.submit, button[type="submit"]')
                if send_button and await send_button.is_visible():
                    await send_button.click()
                    await asyncio.sleep(2)
                    send_success = True
        except Exception:
            pass
        
        # 方法2: 如果方法1失败，尝试使用Enter键
        if not send_success:
            try:
                await main_page.keyboard.press("Enter")
                await asyncio.sleep(2)
                send_success = True
            except Exception:
                pass
        
        # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
        if not send_success:
            try:
                js_send_result = await main_page.evaluate('''
                    () => {
                        const sendButtons = Array.from(document.querySelectorAll('button'))
                            .filter(btn => btn.textContent && 
                                  (btn.textContent.includes('发送') || 
                                   btn.textContent.includes('评论') || 
                                   btn.textContent.includes('提交')));
                        
                        if (sendButtons.length > 0) {
                            sendButtons[0].click();
                            return true;
                        }
                        
                        // 尝试其他可能的发送按钮
                        const otherButtons = Array.from(document.querySelectorAll('button.send-button, button.submit, button[type="submit"]'));
                        if (otherButtons.length > 0) {
                            otherButtons[0].click();
                            return true;
                        }
                        
                        return false;
                    }
                ''')
                await asyncio.sleep(2)
                send_success = js_send_result
            except Exception:
                pass
        
        if send_success:
            return f"已成功发布评论：{comment}"
        else:
            return f"发布评论失败，请检查评论内容或网络连接"
    
    except Exception as e:
        return f"发布评论时出错: {str(e)}"

# 注册同步封装函数，用于直接在Python中调用
def sync_post_comment(url: str, comment: str) -> str:
    """
    同步封装异步post_comment函数，确保返回值为纯字符串
    """
    loop = asyncio.get_event_loop()
    try:
        if loop.is_running():
            coro = post_comment(url, comment)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result()
        else:
            result = loop.run_until_complete(post_comment(url, comment))
        
        # 保证返回值为字符串
        if not isinstance(result, str):
            result = str(result)
        return result
    except Exception as e:
        return f"发布评论时出错: {str(e)}"
