"""
发布相关功能模块，包括发布图文笔记等
"""
import asyncio
import os
from typing import List, Optional
import re


class PublishManager:
    """发布管理类，处理笔记的发布等操作"""
    
    def __init__(self, browser_manager):
        """初始化发布管理器
        
        Args:
            browser_manager: 浏览器管理器实例
        """
        self.browser = browser_manager
    
    async def publish_note(self, title: str, content: str, media_paths: List[str], topics: Optional[List[str]] = None):
        """发布图文或视频笔记
        
        Args:
            title (str): 笔记标题
            content (str): 笔记正文内容
            media_paths (List[str]): 媒体文件路径列表（支持图片和视频）
            topics (Optional[List[str]], optional): 话题标签列表. 默认为None.
        
        Returns:
            str: 操作结果
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号，才能发布笔记"

        # 检测媒体文件类型
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        
        has_video = False
        has_image = False
        
        for media_path in media_paths:
            if not os.path.exists(media_path):
                return f"媒体文件不存在: {media_path}"
            
            file_ext = os.path.splitext(media_path)[1].lower()
            if file_ext in video_extensions:
                has_video = True
            elif file_ext in image_extensions:
                has_image = True
            else:
                return f"不支持的文件类型: {file_ext}"
        
        # 检查是否混合了视频和图片
        if has_video and has_image:
            return "不能同时上传视频和图片，请分别发布"
        
        # 检查视频文件数量
        if has_video and len(media_paths) > 1:
            return "一次只能上传一个视频文件"

        try:
            # 访问小红书创作服务平台
            await self.browser.goto("https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch", wait_time=5)
            
            # 根据文件类型选择对应的模式
            if has_video:
                # 切换到视频模式
                try:
                    video_tab = await self.browser.main_page.query_selector('text="上传视频"')
                    if video_tab:
                        await video_tab.click()
                        await self.browser.main_page.wait_for_selector('div[class*="upload-window"], div[class*="video-upload-area"]', state='visible', timeout=5000)
                        print("已切换到视频模式")
                    else:
                        # 尝试其他视频相关的选择器
                        video_selectors = [
                            'div[data-testid="video-tab"]',
                            'button:has-text("视频")',
                            '.tab-video',
                            '[role="tab"]:has-text("视频")'
                        ]
                        for selector in video_selectors:
                            video_tab = await self.browser.main_page.query_selector(selector)
                            if video_tab:
                                await video_tab.click()
                                await self.browser.main_page.wait_for_selector('div[class*="upload-window"], div[class*="video-upload-area"]', state='visible', timeout=5000)
                                print(f"使用选择器 {selector} 切换到视频模式")
                                break
                except Exception as e:
                    print(f"切换到视频模式时出错: {str(e)}")
                
                # 上传视频文件
                video_path = media_paths[0]
                await self._upload_video(video_path)
                
            else:
                # 切换到图文模式
                try:
                    text_tab = await self.browser.main_page.query_selector('text="上传图文"')
                    if text_tab:
                        await text_tab.click()
                        await self.browser.main_page.wait_for_selector('div[class*="upload-window"], input[type="file"]', state='visible', timeout=5000)
                        print("已切换到图文模式")
                except Exception as e:
                    print(f"切换到图文模式时出错: {str(e)}")
                
                # 上传图片文件
                for img_path in media_paths:
                    await self._upload_image(img_path)
            
            # 输入标题
            try:
                title_selectors = [
                    'input[data-testid="note-title-input"]',
                    'textarea[data-testid="note-title-input"]',
                    'input[name="title"]',
                    '#xhs-note-title-input',
                    'input.note-title-field',
                    'input[aria-label*="标题"]',
                    'textarea[aria-label*="标题"]',
                    'input[placeholder*="标题"]',
                    'textarea[placeholder*="标题"]',
                ]
                title_input = None
                for selector in title_selectors:
                    title_input = await self.browser.main_page.query_selector(selector)
                    if title_input:
                        print(f"Found title input with selector: {selector}")
                        break
                
                if title_input:
                    await title_input.fill(title)
                    await self.browser.main_page.wait_for_timeout(500)
            except Exception as e:
                print(f"输入标题时出错: {str(e)}")
            
            # 输入正文内容（支持#话题自动标签化）
            try:
                content_selectors = [
                    'div.ProseMirror[contenteditable="true"]',
                    'div[data-testid="note-content-editor"][contenteditable="true"]',
                    '#xhs-note-content-editor[contenteditable="true"]',
                    'div.note-content-editor-class[contenteditable="true"]',
                    'textarea[data-testid="note-content-textarea"]',
                    'textarea[placeholder*="输入正文"][aria-label*="正文"]',
                    'div[contenteditable="true"][aria-label*="正文"]',
                    'textarea[placeholder*="输入正文"]',
                    'div[contenteditable="true"]:not([aria-label*="标题"])',
                    '[role="textbox"]:not(input)',
                ]
                content_input = None
                for selector in content_selectors:
                    content_input = await self.browser.main_page.query_selector(selector)
                    if content_input:
                        print(f"Found content input with selector: {selector}")
                        break

                if content_input:
                    await content_input.click()
                    await content_input.wait_for_element_state('editable', timeout=1000)
                    
                    # 输入基础内容
                    await content_input.type(content)
                    await self.browser.main_page.wait_for_timeout(500)
                    
                    # 添加话题标签（在内容末尾）
                    if topics and len(topics) > 0:
                        await content_input.type('\n\n')  # 换行分隔
                        print(f"开始添加话题标签，共 {len(topics)} 个")
                        
                        for i, topic in enumerate(topics):
                            topic_text = f"#{topic}"
                            print(f"输入话题标签: {topic_text}")
                            await content_input.type(topic_text)
                            await self.browser.main_page.wait_for_selector('div[class*="topic-suggestion"], div[class*="el-autocomplete-suggestion"] li', state='visible', timeout=3000)  # 等待下拉建议出现
                            
                            # 等待并查找话题下拉建议列表
                            print("等待话题下拉建议出现...")
                            suggestion_clicked = False
                            
                            # Optimized and prioritized selectors for topic suggestion items
                            suggestion_selectors = [
                                # Ideal: Specific test ID or unique class for a suggestion item
                                'li[data-testid="topic-suggestion-item"]', 
                                'div.xhs-topic-suggestion-item span.topic-name', # Hypothetical specific structure
                                # Common patterns for suggestion lists (e.g., if using Element UI or similar)
                                '.el-autocomplete-suggestion__list li:has-text("#"):first-child',
                                'ul.topic-suggestion-list li.topic-item:has-text("#"):first-child',
                                # Generic role-based selectors if specific classes are unknown
                                'div[role="listbox"] li[role="option"]:has-text("#"):first-child',
                                'div[role="listbox"] div[role="option"]:has-text("#"):first-child',
                                # Fallback to broader class matches (less ideal)
                                'div[class*="suggestion-item"]:has-text("#"):first-child',
                                'li[class*="topic-item"]:has-text("#"):first-child',
                            ]
                            
                            # 尝试每个选择器
                            for selector in suggestion_selectors:
                                try:
                                    print(f"尝试选择器: {selector}")
                                    suggestion = await self.browser.main_page.query_selector(selector)
                                    if suggestion:
                                        is_visible = await suggestion.is_visible()
                                        print(f"找到建议项，可见性: {is_visible}")
                                        if is_visible:
                                            # 获取建议项的文本内容
                                            suggestion_text = await suggestion.text_content()
                                            print(f"建议项文本: {suggestion_text}")
                                            
                                            await suggestion.click()
                                            await self.browser.main_page.wait_for_timeout(1000)
                                            suggestion_clicked = True
                                            print(f"成功点击话题建议: {suggestion_text}")
                                            break
                                except Exception as sel_e:
                                    print(f"选择器 {selector} 失败: {str(sel_e)}")
                                    continue
                            
                            # 如果标准选择器都没找到，尝试JavaScript查找
                            if not suggestion_clicked:
                                print("尝试使用JavaScript查找话题建议...")
                                js_click_result = await self.browser.main_page.evaluate(f'''
                                    (topicText) => {{
                                        const suggestionContainerSelectors = [
                                            '.xhs-topic-suggestions-dropdown', // Hypothetical specific container
                                            '.el-autocomplete-suggestion__wrap',
                                            'div[class*="topic-suggestion-list"]',
                                            'ul[role="listbox"][aria-label*="话题"]'
                                        ];
                                        let container = null;
                                        for (const sel of suggestionContainerSelectors) {{
                                            container = document.querySelector(sel);
                                            if (container) break;
                                        }}
                                        if (!container) {{
                                            // If no specific container, fallback to a wider search area, 
                                            // but this is less reliable.
                                            container = document.body; 
                                            console.warn("Topic suggestion container not found, JS fallback might be slow/unreliable.");
                                        }}

                                        const items = Array.from(container.querySelectorAll('li[role="option"], div[role="option"], .suggestion-item, .topic-item'));
                                        let targetItem = items.find(item => 
                                            item.textContent && item.textContent.includes(topicText) && item.offsetParent !== null
                                        );

                                        if (!targetItem) {{ // Broader search if exact match fails
                                            targetItem = items.find(item => 
                                                item.textContent && item.textContent.includes(topicText.replace("#","")) && item.offsetParent !== null
                                            );
                                        }}
                                        
                                        if (targetItem) {{
                                            targetItem.style.border = '3px solid red'; // For visual debugging if needed
                                            targetItem.click();
                                            return {{
                                                success: true,
                                                text: targetItem.textContent.trim(),
                                                found: items.length
                                            }};
                                        }}
                                        return {{ success: false, found: items.length }};
                                    }}
                                ''', f"#{topic}") // Pass topic with #
                                
                                print(f"JavaScript点击结果: {js_click_result}")
                                if js_click_result.get('success'):
                                    suggestion_clicked = True
                                    print(f"JavaScript成功点击建议: {js_click_result.get('text')}")
                            
                            if not suggestion_clicked:
                                print(f"未找到话题建议项，标签 {topic_text} 可能未被激活")
                                # 按回车或空格尝试确认
                                await content_input.press('Enter')
                                await self.browser.main_page.wait_for_timeout(500)
                            
                            # 如果不是最后一个话题，添加空格
                            if i < len(topics) - 1:
                                await content_input.type(' ')
                                await self.browser.main_page.wait_for_timeout(500)
                        
                        print("话题标签添加完成")
                    
                    await self.browser.main_page.wait_for_timeout(1000)
                else:
                    print("未找到内容输入框，使用兼容逻辑")
                    # 兼容原有逻辑
                    await self.browser.main_page.evaluate('''
                        () => {
                            const textareas = Array.from(document.querySelectorAll('textarea, [contenteditable="true"]'));
                            const contentArea = textareas.find(el => 
                                el.placeholder && (
                                    el.placeholder.includes('输入') || 
                                    el.placeholder.includes('描述') || 
                                    el.placeholder.includes('正文')
                                )
                            );
                            if (contentArea) contentArea.focus();
                            return !!contentArea;
                        }
                    ''')
                    # 构建包含话题标签的完整内容
                    full_content = content
                    if topics and len(topics) > 0:
                        topic_tags = ' '.join([f'#{topic}' for topic in topics])
                        full_content = f"{content}\n\n{topic_tags}"
                    
                    await self.browser.main_page.keyboard.type(full_content)
                    await self.browser.main_page.wait_for_timeout(1000)
            except Exception as e:
                print(f"输入正文内容时出错: {str(e)}")
            
            # 立即发布（默认选择立即发布）
            immediate_publish = await self.browser.main_page.query_selector('text="立即发布"')
            if immediate_publish:
                # 确保选择立即发布
                await immediate_publish.click()
                await self.browser.main_page.wait_for_timeout(1000)
            
            # 点击发布按钮
            publish_button_selectors = [
                'button[data-testid="publish-note-button"]',
                'button#publish-note-btn',
                'button.publish-button-primary',
                'button.xhs-publish-button[type="button"]',
                'button[aria-label="立即发布"]',
                'button:has-text("发布笔记")' , # More specific text first
                'button:has-text("发布")',
                '[aria-label="发布"]', # Most generic, last resort
            ]
            publish_button = None
            for selector in publish_button_selectors:
                publish_button = await self.browser.main_page.query_selector(selector)
                if publish_button:
                    print(f"Found publish button with selector: {selector}")
                    break
            
            if publish_button:
                await publish_button.click()
                await self.browser.main_page.wait_for_selector('text*="发布成功", text*="笔记发布成功", div[class*="success-toast"]', timeout=15000)  # 等待发布完成
                
                # 检查是否有发布成功的提示
                success_message = await self.browser.main_page.query_selector('text="发布成功"')
                if success_message:
                    return "笔记发布成功"
                
                # 检查是否有错误提示
                error_message = await self.browser.main_page.query_selector('.error-message, .toast-message')
                if error_message:
                    error_text = await error_message.text_content()
                    return f"发布失败: {error_text}"
                
                return "笔记已提交发布，但未收到明确的成功反馈"
            else:
                return "未找到发布按钮，笔记发布失败"
        
        except Exception as e:
            return f"发布笔记时出错: {str(e)}"

    async def _upload_image(self, img_path: str):
        """上传图片文件
        
        Args:
            img_path (str): 图片文件路径
        """
        try:
            if not os.path.exists(img_path):
                print(f"图片不存在: {img_path}")
                return
            
            print(f"尝试上传图片: {img_path}")
            
            # 截图保存当前界面状态（用于调试）
            try:
                screenshot_path = os.path.join(os.path.dirname(img_path), "page_screenshot.png")
                await self.browser.main_page.screenshot(path=screenshot_path)
                print(f"已保存页面截图到: {screenshot_path}")
            except Exception as ss_e:
                print(f"截图失败: {str(ss_e)}")
            
            # Optimized and prioritized selectors for the image upload trigger
            # The goal is to click the visible element that opens the file dialog
            upload_trigger_selectors = [
                'button[data-testid="image-upload-trigger-button"]', # Ideal: specific test ID
                '#image-upload-button-id',                          # Ideal: specific ID
                'button.xhs-image-upload-button',                   # Ideal: specific class
                'button.custom-upload-btn-image',                   # Another hypothetical specific class
                'div.image-upload-area button:has-text("上传图片")',  # Button with text in a defined area
                'div.image-upload-area button:has-text("添加图片")',
                'button:has-text("上传图片")',                        # General button with text
                # Fallbacks if specific selectors fail
                '.upload-image-btn',
                'button.upload-btn',
                '.el-upload button', # If Element UI is used
            ]

            upload_trigger = None
            for selector in upload_trigger_selectors:
                trigger = await self.browser.main_page.query_selector(selector)
                if trigger and await trigger.is_visible(): # Ensure the trigger is visible
                    upload_trigger = trigger
                    print(f"Found visible image upload trigger with selector: {selector}")
                    break
            
            # If a trigger is found, use file_chooser; otherwise, try direct input (less common for styled uploads)
            if upload_trigger:
                print("Visible image upload trigger found, preparing to click and use file chooser.")
                
                # 检查按钮是否可见和可点击
                is_visible = await upload_button.is_visible()
                print(f"按钮可见: {is_visible}")
                
                try:
                    async with self.browser.main_page.expect_file_chooser(timeout=10000) as fc_info:
                        await upload_trigger.click()
                        print(f"Clicked image upload trigger: {await upload_trigger.text_content()}")
                    
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(img_path)
                    print(f"Successfully set files using file_chooser for image: {img_path}")
                    await self.browser.main_page.wait_for_timeout(3000) # Wait for upload to process
                    return # Successfully uploaded
                except Exception as e:
                    print(f"Using file_chooser for image upload failed: {e}. Will attempt direct input if possible.")

            # Fallback or alternative: Try to find a specific, possibly hidden, file input and set files directly
            # This is useful if the button doesn't reliably trigger a file chooser event recognized by Playwright
            # or if the input becomes available/targetable after some other interactions.
            direct_file_input_selectors = [
                'input[type="file"][data-testid="image-file-input"]', # Ideal: specific test ID for the input
                'input[type="file"][name="image_upload"]',          # Common name attribute
                '#hidden-image-uploader-input',                      # Hypothetical specific ID for a hidden input
                'input[type="file"][accept^="image/"]',             # Standard file input for images
                'input.xhs-image-file-input',                        # Hypothetical specific class for the input
            ]
            file_input_element = None
            for selector in direct_file_input_selectors:
                element = await self.browser.main_page.query_selector(selector)
                # Check if element exists and is not the one already tried if upload_trigger was an input
                if element and (not upload_trigger or await element.evaluate_handle('(el, trigger) => el !== trigger', upload_trigger) if upload_trigger else True) :
                    file_input_element = element
                    print(f"Found direct image file input with selector: {selector}")
                    break
            
            if file_input_element:
                try:
                    await file_input_element.set_input_files(img_path)
                    print(f"Successfully set files directly to image input: {img_path}")
                    await self.browser.main_page.wait_for_timeout(3000) # Wait for upload
                    return # Successfully uploaded
                except Exception as e:
                    print(f"Setting files directly to image input failed: {e}")
            
            if not upload_trigger and not file_input_element:
                 print("No visible image upload trigger or direct file input found after optimizations.")

            
        except Exception as e:
            print(f"上传图片过程中出错: {str(e)}")
    
    async def _upload_video(self, video_path: str):
        """上传视频文件
        
        Args:
            video_path (str): 视频文件路径
        """
        try:
            if not os.path.exists(video_path):
                print(f"视频不存在: {video_path}")
                return
            
            print(f"尝试上传视频: {video_path}")
            
            # Optimized and prioritized selectors for the video upload trigger
            upload_trigger_selectors = [
                'button[data-testid="video-upload-trigger-button"]',
                '#video-upload-trigger-id',
                'button.xhs-video-upload-button',
                'div.video-upload-area button:has-text("上传视频")',
                'div.video-upload-area button:has-text("选择视频")',
                'button:has-text("上传视频")', # General buttons
                'button:has-text("选择视频")',
                '.video-upload-btn', # Class-based fallbacks
                '.upload-video-btn',
                '.el-upload button[accept*="video"]', # Element UI specific
            ]

            upload_trigger = None
            for selector in upload_trigger_selectors:
                trigger = await self.browser.main_page.query_selector(selector)
                if trigger and await trigger.is_visible():
                    upload_trigger = trigger
                    print(f"Found visible video upload trigger with selector: {selector}")
                    break

            if upload_trigger:
                print("Visible video upload trigger found, preparing to click and use file chooser.")
                try:
                    async with self.browser.main_page.expect_file_chooser(timeout=10000) as fc_info:
                        await upload_trigger.click()
                        print(f"Clicked video upload trigger: {await upload_trigger.text_content()}")
                    
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(video_path)
                    print(f"Successfully set files using file_chooser for video: {video_path}")
                    await self.browser.main_page.wait_for_timeout(5000) # Wait for upload
                    return # Successfully uploaded
                except Exception as e:
                    print(f"Using file_chooser for video upload failed: {e}. Will attempt direct input.")

            # Fallback or alternative: Try to find a specific, possibly hidden, video file input
            direct_file_input_selectors = [
                'input[type="file"][data-testid="video-file-input"]',
                'input[type="file"][name="video_upload"]',
                '#hidden-video-uploader-input',
                'input[type="file"][accept*="video"]', # Standard and most reliable for video
                'input.xhs-video-file-input',
            ]
            file_input_element = None
            for selector in direct_file_input_selectors:
                element = await self.browser.main_page.query_selector(selector)
                if element and (not upload_trigger or await element.evaluate_handle('(el, trigger) => el !== trigger', upload_trigger) if upload_trigger else True):
                    file_input_element = element
                    print(f"Found direct video file input with selector: {selector}")
                    break
            
            if file_input_element:
                try:
                    await file_input_element.set_input_files(video_path)
                    print(f"Successfully set files directly to video input: {video_path}")
                    await self.browser.main_page.wait_for_timeout(5000) # Wait for upload
                    return # Successfully uploaded
                except Exception as e:
                    print(f"Setting files directly to video input failed: {e}")

            # If both trigger and direct input methods fail, try JavaScript fallback
            if not upload_trigger and not file_input_element:
                print("Python selectors for video upload failed. Attempting JavaScript fallback.")
                js_upload_success = await self.browser.main_page.evaluate('''
                    async (filePath) => { // filePath will be passed as an argument from Python
                        // Priority 1: Specific file input for videos
                        let videoInput = document.querySelector('input[type="file"][accept*="video"]');
                        if (videoInput && videoInput.offsetParent === null) { // if hidden, try to find its label
                            const label = document.querySelector(`label[for="${videoInput.id}"]`);
                            if (label) label.click(); // Click label to potentially show input or trigger dialog
                        }
                        // If still no direct input visible or clickable, try buttons
                        if (!videoInput || videoInput.offsetParent === null) {
                            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
                            const uploadButton = buttons.find(b => 
                                b.textContent && 
                                (b.textContent.includes('上传视频') || b.textContent.includes('选择视频')) &&
                                b.offsetParent !== null
                            );
                            if (uploadButton) {
                                uploadButton.click(); // This should trigger the file chooser
                                // Playwright's set_input_files or file_chooser must handle the dialog opened by this click
                                // This JS function can't directly set files to a dialog it merely opens.
                                // It can, however, set files if it finds a *direct, visible* file input.
                                console.log('JS clicked a video upload button. File dialog should be open.');
                                return { clickedButton: true, foundDirectInput: false }; 
                            }
                        }
                        // Try to use a direct input if found (even if not initially visible, set_input_files might work)
                        if (videoInput) {
                             console.log('JS found a direct video input. Playwright should use set_input_files on this.');
                            // Cannot set files from evaluate, this is a marker for Playwright
                            return { clickedButton: false, foundDirectInput: true, selector: 'input[type="file"][accept*="video"]' };
                        }
                        return { clickedButton: false, foundDirectInput: false };
                    }
                ''') # We don't pass filePath here as JS cannot set files to dialogs.

                if js_upload_success and js_upload_success.get('clickedButton'):
                    print("JavaScript fallback clicked an upload button. Waiting for file chooser.")
                    try:
                        async with self.browser.main_page.expect_file_chooser(timeout=10000) as fc_info:
                            # The click was already performed by JS, we are just waiting for the chooser
                            print("JS already clicked, now just expecting chooser.")
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(video_path)
                        print(f"Successfully set video files via JS-triggered file_chooser: {video_path}")
                        await self.browser.main_page.wait_for_timeout(5000)
                        return
                    except Exception as e:
                        print(f"JS-triggered file_chooser for video failed: {e}")
                elif js_upload_success and js_upload_success.get('foundDirectInput'):
                    print("JavaScript fallback identified a direct input. Attempting to set files via Playwright.")
                    direct_input = await self.browser.main_page.query_selector(js_upload_success.get('selector'))
                    if direct_input:
                        try:
                            await direct_input.set_input_files(video_path)
                            print(f"Successfully set video files to JS-identified direct input: {video_path}")
                            await self.browser.main_page.wait_for_timeout(5000)
                            return
                        except Exception as e:
                             print(f"Setting files to JS-identified direct video input failed: {e}")
                else:
                    print("All video upload attempts, including JavaScript fallback, failed.")
            
        except Exception as e:
            print(f"上传视频过程中出错: {str(e)}") 