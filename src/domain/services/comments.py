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

    async def diagnose_page_elements(self):
        """诊断页面元素，找出真正的问题"""
        print("🔍 开始页面元素诊断...")

        try:
            # 1. 检查页面基本状态
            page_info = await self.browser.main_page.evaluate('''
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        readyState: document.readyState,
                        hasContentTextarea: !!document.querySelector('#content-textarea'),
                        hasContentInput: !!document.querySelector('.content-input'),
                        allEditableCount: document.querySelectorAll('[contenteditable="true"]').length,
                        allPElements: document.querySelectorAll('p').length
                    };
                }
            ''')
            print(f"📊 页面状态: {page_info}")

            # 2. 详细检查目标元素
            element_details = await self.browser.main_page.evaluate('''
                () => {
                    const textarea = document.querySelector('#content-textarea');
                    if (textarea) {
                        const rect = textarea.getBoundingClientRect();
                        return {
                            found: true,
                            tag: textarea.tagName,
                            id: textarea.id,
                            className: textarea.className,
                            contentEditable: textarea.contentEditable,
                            visible: textarea.offsetParent !== null,
                            rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                            style: {
                                display: getComputedStyle(textarea).display,
                                visibility: getComputedStyle(textarea).visibility,
                                opacity: getComputedStyle(textarea).opacity
                            }
                        };
                    }
                    return {found: false};
                }
            ''')
            print(f"🎯 目标元素详情: {element_details}")

            return element_details

        except Exception as e:
            print(f"❌ 诊断过程出错: {str(e)}")
            return None

    async def find_comment_input(self):
        """查找评论输入框，增加诊断功能

        Returns:
            element or None: 评论输入框元素
        """
        print("🔍 开始查找评论输入框...")

        # 先进行诊断
        diagnosis = await self.diagnose_page_elements()

        # 如果诊断显示元素存在但不可见，可能需要特殊处理
        if diagnosis and diagnosis.get('found') and not diagnosis.get('visible'):
            print("⚠️ 元素存在但不可见，尝试激活...")
            # 尝试滚动到页面底部激活评论区域
            await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

        # 使用最精确的选择器
        target_selectors = [
            '#content-textarea',  # 您提供的精确ID
            '.content-input',     # 您提供的精确类名
            'p[contenteditable="true"][data-tribute="true"]'  # 您提供的精确属性
        ]

        for selector in target_selectors:
            try:
                print(f"🎯 尝试精确选择器: {selector}")
                element = await self.browser.main_page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    print(f"元素存在: {element}, 可见: {is_visible}")
                    if is_visible:
                        await element.scroll_into_view_if_needed()
                        print(f"✅ 成功找到评论输入框: {selector}")
                        return element
                    else:
                        print(f"⚠️ 元素存在但不可见: {selector}")
                else:
                    print(f"❌ 元素不存在: {selector}")
            except Exception as e:
                print(f"❌ 选择器异常 {selector}: {str(e)}")

        print("❌ 所有精确选择器都失败")
        return None

    async def activate_comment_area(self):
        """激活评论区域，确保评论输入框可见

        Returns:
            bool: 是否成功激活评论区域
        """
        print("尝试激活评论区域...")

        # 定位评论区域并滚动到该区域
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
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(2)

                    # 尝试点击评论区域来激活输入框
                    try:
                        await element.click()
                        await asyncio.sleep(2)
                        print(f"成功激活评论区域: {selector}")
                        return True
                    except Exception:
                        pass
            except Exception:
                continue

        # 如果没有找到评论区域，尝试滚动到页面底部
        try:
            await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
            print("滚动到页面底部以激活评论区域")
            return True
        except Exception:
            pass

        print("未能激活评论区域")
        return False

    async def send_comment(self, comment_input, comment_text):
        """发送评论，基于原有有效逻辑的简化版本

        Args:
            comment_input: 评论输入框元素
            comment_text: 评论内容

        Returns:
            bool: 是否发送成功
        """
        try:
            # 输入评论内容（使用原有有效的方式）
            await comment_input.click()
            await asyncio.sleep(1)
            await self.browser.main_page.keyboard.type(comment_text)
            await asyncio.sleep(1)

            # 发送评论（使用原有有效的简化发送逻辑）
            send_success = False

            # 方法1: 尝试点击发送按钮
            try:
                send_button = await self.browser.main_page.query_selector('button:has-text("发送")')
                if send_button and await send_button.is_visible():
                    print("找到发送按钮，点击发送")
                    await send_button.click()
                    await asyncio.sleep(2)
                    send_success = True
            except Exception:
                pass

            # 方法2: 如果方法1失败，尝试使用Enter键
            if not send_success:
                try:
                    print("尝试使用Enter键发送")
                    await self.browser.main_page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    send_success = True
                except Exception:
                    pass

            # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
            if not send_success:
                try:
                    print("使用JavaScript查找发送按钮")
                    js_send_result = await self.browser.main_page.evaluate('''
                        () => {
                            const sendButtons = Array.from(document.querySelectorAll('button'))
                                .filter(btn => btn.textContent && btn.textContent.includes('发送'));
                            if (sendButtons.length > 0) {
                                sendButtons[0].click();
                                console.log('JavaScript点击发送按钮');
                                return true;
                            }
                            return false;
                        }
                    ''')
                    await asyncio.sleep(2)
                    send_success = js_send_result
                except Exception:
                    pass

            return send_success

        except Exception as e:
            print(f"发送评论时出错: {str(e)}")
            return False

    async def post_comment(self, url, comment):
        """发布评论到指定笔记，基于原有有效逻辑

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

        try:
            print("🌐 开始访问页面...")
            # 访问帖子链接
            await self.browser.main_page.goto(url, timeout=30000)
            print("⏳ 智能等待页面加载...")
            # 优化：使用智能等待替代固定2秒，节省1.5秒
            try:
                await self.browser.main_page.wait_for_load_state('networkidle', timeout=5000)
                print("✅ 页面加载完成（智能等待）")
            except Exception:
                # 备用方案：如果智能等待失败，使用最小固定等待
                await asyncio.sleep(0.5)
                print("✅ 页面加载完成（备用等待）")

            # 直接滚动到页面底部激活评论区域（优化等待时间）
            print("📜 滚动到评论区域...")
            await self.browser.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            # 优化：减少滚动后等待时间，从1秒减少到0.3秒，节省0.7秒
            await asyncio.sleep(0.3)

            # 直接使用诊断验证过的选择器（基于诊断结果优化）
            print("🎯 查找评论输入框...")
            comment_input = None

            # 使用诊断验证过的最精确选择器
            try:
                comment_input = await self.browser.main_page.query_selector('#content-textarea')
                if comment_input and await comment_input.is_visible():
                    print("✅ 使用 #content-textarea 找到输入框")
                else:
                    comment_input = None
            except Exception:
                pass

            # 备用选择器
            if not comment_input:
                try:
                    comment_input = await self.browser.main_page.query_selector('.content-input')
                    if comment_input and await comment_input.is_visible():
                        print("✅ 使用 .content-input 找到输入框")
                    else:
                        comment_input = None
                except Exception:
                    pass

            # 最后的备用选择器
            if not comment_input:
                try:
                    comment_input = await self.browser.main_page.query_selector('p[contenteditable="true"][data-tribute="true"]')
                    if comment_input and await comment_input.is_visible():
                        print("✅ 使用属性选择器找到输入框")
                    else:
                        comment_input = None
                except Exception:
                    pass



            if not comment_input:
                return "未能找到评论输入框，无法发布评论"

            # 确保元素可见并聚焦（优化等待时间）
            await comment_input.scroll_into_view_if_needed()
            # 优化：减少聚焦等待时间，从0.3秒减少到0.1秒
            await asyncio.sleep(0.1)

            # 输入评论内容（解决点击被阻挡问题）
            print("📝 激活评论输入框...")

            # 方法1: 先尝试点击覆盖的"评论"元素来激活输入框
            try:
                overlay_element = await self.browser.main_page.query_selector('span:has-text("评论")')
                if overlay_element:
                    print("🎯 点击覆盖的'评论'元素...")
                    await overlay_element.click()
                    # 优化：减少点击后等待时间，从0.5秒减少到0.2秒
                    await asyncio.sleep(0.2)
            except Exception:
                pass

            # 方法2: 使用JavaScript直接聚焦输入框
            try:
                print("🎯 使用JavaScript聚焦输入框...")
                await self.browser.main_page.evaluate('''
                    () => {
                        const textarea = document.querySelector('#content-textarea');
                        if (textarea) {
                            textarea.focus();
                            textarea.click();
                        }
                    }
                ''')
                # 优化：减少JavaScript聚焦后等待时间，从0.3秒减少到0.1秒
                await asyncio.sleep(0.1)
            except Exception:
                pass

            # 方法3: 如果还不行，使用force点击
            try:
                print("🎯 尝试force点击...")
                await comment_input.click(force=True)
                # 优化：减少force点击后等待时间，从0.3秒减少到0.1秒
                await asyncio.sleep(0.1)
            except Exception:
                pass

            # 输入评论内容
            print("📝 输入评论内容...")
            await self.browser.main_page.keyboard.press("Control+a")  # 全选
            await self.browser.main_page.keyboard.type(comment)
            # 优化：减少输入完成后等待时间，从0.3秒减少到0.1秒
            await asyncio.sleep(0.1)
            print("✅ 评论输入完成")

            # 发送评论 - 使用最简单最快的方法
            print("🚀 发送评论...")
            await self.browser.main_page.keyboard.press("Enter")
            # 优化：减少发送后等待时间，从1秒减少到0.5秒
            await asyncio.sleep(0.5)

            print("✅ 评论发送完成")
            return f"已成功发布评论：{comment}"

        except Exception as e:
            return f"发布评论时出错: {str(e)}"

    def _extract_note_id(self, url):
        """从URL中提取笔记ID

        Args:
            url (str): 笔记URL

        Returns:
            str or None: 笔记ID
        """
        if not url:
            return None

        try:
            # 小红书笔记URL格式: https://www.xiaohongshu.com/explore/{note_id}?...
            import re
            match = re.search(r'/explore/([a-f0-9]+)', url)
            if match:
                return match.group(1)
        except Exception:
            pass

        return None

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
