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
                        await asyncio.sleep(3)
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
                                await asyncio.sleep(3)
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
                        await asyncio.sleep(2)
                        print("已切换到图文模式")
                except Exception as e:
                    print(f"切换到图文模式时出错: {str(e)}")
                
                # 上传图片文件
                for img_path in media_paths:
                    await self._upload_image(img_path)
            
            # 输入标题
            try:
                title_input = await self.browser.main_page.query_selector('input[placeholder*="标题"], textarea[placeholder*="标题"]')
                if title_input:
                    await title_input.fill(title)
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"输入标题时出错: {str(e)}")
            
            # 输入正文内容（支持#话题自动标签化）
            try:
                content_input = await self.browser.main_page.query_selector('div[contenteditable="true"], textarea[placeholder*="输入正文"], [role="textbox"]')
                if content_input:
                    await content_input.click()
                    await asyncio.sleep(0.5)
                    
                    # 输入基础内容
                    await content_input.type(content)
                    await asyncio.sleep(0.5)
                    
                    # 添加话题标签（在内容末尾）
                    if topics and len(topics) > 0:
                        await content_input.type('\n\n')  # 换行分隔
                        print(f"开始添加话题标签，共 {len(topics)} 个")
                        
                        for i, topic in enumerate(topics):
                            topic_text = f"#{topic}"
                            print(f"输入话题标签: {topic_text}")
                            await content_input.type(topic_text)
                            await asyncio.sleep(2)  # 等待下拉建议出现
                            
                            # 等待并查找话题下拉建议列表
                            print("等待话题下拉建议出现...")
                            suggestion_clicked = False
                            
                            # 尝试多种选择器来找到下拉建议
                            suggestion_selectors = [
                                # 基于截图中的结构，话题建议可能在这些容器中
                                'div[class*="topic"] div[class*="item"]:first-child',
                                'div[class*="suggestion"] div[class*="item"]:first-child',
                                '.topic-suggestion-list .topic-item:first-child',
                                '.suggestion-dropdown .suggestion-item:first-child',
                                # Element UI 相关选择器
                                '.el-select-dropdown__item:first-child',
                                '.el-autocomplete-suggestion__list li:first-child',
                                '.el-autocomplete-suggestion li:first-child',
                                # 通用的下拉列表选择器
                                'ul li:first-child',
                                'div[role="option"]:first-child',
                                'li[role="option"]:first-child',
                                # 可能的话题容器
                                '.topic-dropdown .topic-option:first-child',
                                '.hashtag-dropdown .hashtag-option:first-child'
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
                                            await asyncio.sleep(1)
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
                                    () => {{
                                        // 查找包含话题文本的元素
                                        const allElements = Array.from(document.querySelectorAll('div, li, span, a'));
                                        
                                        // 寻找包含当前话题关键词的建议项
                                        const topicKeyword = "{topic}";
                                        const suggestionItems = allElements.filter(el => {{
                                            const text = el.textContent;
                                            return text && (
                                                text.includes('#{topic}') ||
                                                text.includes(topicKeyword) ||
                                                text.includes('次浏览')
                                            );
                                        }});
                                        
                                        if (suggestionItems.length > 0) {{
                                            // 优先选择完全匹配的项
                                            let targetItem = suggestionItems.find(el => 
                                                el.textContent.includes('#{topic}')
                                            );
                                            
                                            // 如果没有完全匹配，选择第一个相关项
                                            if (!targetItem) {{
                                                targetItem = suggestionItems[0];
                                            }}
                                            
                                            // 高亮并点击
                                            targetItem.style.border = '3px solid red';
                                            targetItem.click();
                                            
                                            return {{
                                                success: true,
                                                text: targetItem.textContent.trim(),
                                                found: suggestionItems.length
                                            }};
                                        }}
                                        
                                        return {{ success: false, found: 0 }};
                                    }}
                                ''')
                                
                                print(f"JavaScript点击结果: {js_click_result}")
                                if js_click_result.get('success'):
                                    suggestion_clicked = True
                                    print(f"JavaScript成功点击建议: {js_click_result.get('text')}")
                            
                            if not suggestion_clicked:
                                print(f"未找到话题建议项，标签 {topic_text} 可能未被激活")
                                # 按回车或空格尝试确认
                                await content_input.press('Enter')
                                await asyncio.sleep(0.5)
                            
                            # 如果不是最后一个话题，添加空格
                            if i < len(topics) - 1:
                                await content_input.type(' ')
                                await asyncio.sleep(0.5)
                        
                        print("话题标签添加完成")
                    
                    await asyncio.sleep(1)
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
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"输入正文内容时出错: {str(e)}")
            
            # 立即发布（默认选择立即发布）
            immediate_publish = await self.browser.main_page.query_selector('text="立即发布"')
            if immediate_publish:
                # 确保选择立即发布
                await immediate_publish.click()
                await asyncio.sleep(1)
            
            # 点击发布按钮
            publish_button = await self.browser.main_page.query_selector('button:has-text("发布"), button:has-text("发布笔记"), [aria-label="发布"]')
            if publish_button:
                await publish_button.click()
                await asyncio.sleep(5)  # 等待发布完成
                
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
            
            # 查找红色上传图片按钮 - 基于截图中的视觉特征添加精确选择器
            red_upload_button_selectors = [
                'button.el-button--danger',  # 红色按钮类
                '.el-button--danger',        # 红色按钮类
                'button.upload-btn',         # 上传按钮
                '.upload-image-btn',         # 上传图片按钮
                'button.upload-image-btn',   # 上传图片按钮
                '.upload-btn',               # 上传按钮
                'button:has-text("上传图片")',  # 文本匹配
                '.el-upload button',         # Element UI上传组件的按钮
                '.el-upload__input',         # Element UI上传组件的输入
                '.upload-area button',       # 上传区域中的按钮
                '.upload-btn--primary',      # 主要上传按钮
                '.upload-container button'   # 上传容器中的按钮
            ]
            
            # 首先尝试直接找到输入元素
            file_input = await self.browser.main_page.query_selector('input[type="file"]')
            if file_input:
                print("找到文件输入元素，直接设置文件")
                await file_input.set_input_files(img_path)
                print(f"已直接设置文件: {img_path}")
                await asyncio.sleep(3)  # 等待图片上传
                return  # 如果成功直接设置文件，跳过后续尝试
                        
            # 尝试具体的红色上传按钮选择器
            upload_button = None
            for selector in red_upload_button_selectors:
                print(f"尝试红色上传按钮选择器: {selector}")
                button = await self.browser.main_page.query_selector(selector)
                if button:
                    upload_button = button
                    print(f"找到红色上传按钮，使用选择器: {selector}")
                    break
            
            # 如果找到红色上传按钮，尝试点击上传
            if upload_button:
                print("找到红色上传按钮，准备上传图片")
                
                # 检查按钮是否可见和可点击
                is_visible = await upload_button.is_visible()
                print(f"按钮可见: {is_visible}")
                
                # 使用fileChooser处理文件上传
                try:
                    # 设置较长的超时时间等待文件选择器
                    file_chooser_promise = self.browser.main_page.wait_for_file_chooser(timeout=10000)
                    await upload_button.click()
                    print("已点击红色上传按钮")
                    
                    try:
                        file_chooser = await file_chooser_promise
                        await file_chooser.set_files(img_path)
                        print(f"已设置文件: {img_path}")
                        await asyncio.sleep(3)  # 等待图片上传
                    except Exception as fc_e:
                        print(f"等待文件选择器出错: {str(fc_e)}")
                        
                        # 如果文件选择器没出现，尝试直接查找文件输入元素
                        try:
                            await asyncio.sleep(1)  # 等待可能的DOM变化
                            file_input = await self.browser.main_page.query_selector('input[type="file"]')
                            if file_input:
                                print("点击按钮后找到文件输入元素")
                                await file_input.set_input_files(img_path)
                                print(f"已设置文件: {img_path}")
                                await asyncio.sleep(3)  # 等待图片上传
                        except Exception as fi_e:
                            print(f"尝试找文件输入元素出错: {str(fi_e)}")
                except Exception as click_e:
                    print(f"点击上传按钮出错: {str(click_e)}")
            
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
            
            # 查找视频上传相关的按钮和输入元素
            video_upload_selectors = [
                'input[type="file"][accept*="video"]',  # 接受视频的文件输入
                'input[type="file"]',                   # 通用文件输入
                'button:has-text("上传视频")',          # 上传视频按钮
                'button:has-text("选择视频")',          # 选择视频按钮
                '.video-upload-btn',                   # 视频上传按钮类
                '.upload-video-btn',                   # 上传视频按钮类
                '.el-upload button',                   # Element UI上传组件的按钮
                '.upload-area',                        # 上传区域
                '.video-upload-area'                   # 视频上传区域
            ]
            
            # 首先尝试直接找到视频文件输入元素
            for selector in video_upload_selectors:
                print(f"尝试视频上传选择器: {selector}")
                element = await self.browser.main_page.query_selector(selector)
                if element:
                    element_tag = await element.evaluate('el => el.tagName')
                    if element_tag == 'INPUT':
                        print("找到视频文件输入元素，直接设置文件")
                        await element.set_input_files(video_path)
                        print(f"已直接设置视频文件: {video_path}")
                        await asyncio.sleep(5)  # 视频上传需要更长时间
                        return
                    else:
                        # 如果是按钮，尝试点击
                        print(f"找到视频上传按钮: {selector}")
                        try:
                            file_chooser_promise = self.browser.main_page.wait_for_file_chooser(timeout=10000)
                            await element.click()
                            print("已点击视频上传按钮")
                            
                            file_chooser = await file_chooser_promise
                            await file_chooser.set_files(video_path)
                            print(f"已设置视频文件: {video_path}")
                            await asyncio.sleep(5)  # 视频上传需要更长时间
                            return
                        except Exception as e:
                            print(f"点击视频上传按钮失败: {str(e)}")
                            continue
            
            # 如果找不到特定的视频上传元素，尝试通用的文件上传
            print("未找到特定的视频上传元素，尝试通用文件上传方式")
            
            # 使用JavaScript查找上传元素
            js_result = await self.browser.main_page.evaluate('''
                () => {
                    // 查找包含"上传视频"、"选择视频"等文本的按钮
                    const textElements = Array.from(document.querySelectorAll('button, a, div, span'));
                    const videoUploadBtn = textElements.find(el => 
                        el.textContent && (
                            el.textContent.includes('上传视频') ||
                            el.textContent.includes('选择视频') ||
                            el.textContent.includes('添加视频')
                        )
                    );
                    
                    if (videoUploadBtn) {
                        videoUploadBtn.style.border = '5px solid green';
                        return {
                            found: true,
                            method: 'text',
                            tag: videoUploadBtn.tagName,
                            text: videoUploadBtn.textContent.trim()
                        };
                    }
                    
                    // 查找所有文件输入元素
                    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
                    if (fileInputs.length > 0) {
                        fileInputs[0].style.border = '5px solid blue';
                        return {
                            found: true,
                            method: 'input',
                            tag: fileInputs[0].tagName,
                            accept: fileInputs[0].accept || 'none'
                        };
                    }
                    
                    // 查找上传区域
                    const uploadAreas = Array.from(document.querySelectorAll('.upload-area, .el-upload, [class*="upload"]'));
                    if (uploadAreas.length > 0) {
                        uploadAreas[0].style.border = '5px solid yellow';
                        return {
                            found: true,
                            method: 'area',
                            tag: uploadAreas[0].tagName,
                            classes: uploadAreas[0].className
                        };
                    }
                    
                    return { found: false };
                }
            ''')
            
            print(f"JavaScript查找视频上传元素结果: {js_result}")
            
            if js_result.get('found'):
                # 根据查找结果尝试上传
                method = js_result.get('method')
                if method == 'input':
                    # 直接使用文件输入
                    file_input = await self.browser.main_page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(video_path)
                        print(f"通过文件输入设置视频: {video_path}")
                        await asyncio.sleep(5)
                else:
                    # 尝试点击按钮或区域
                    clicked = await self.browser.main_page.evaluate('''
                        () => {
                            const highlightedElements = Array.from(document.querySelectorAll('[style*="border: 5px solid"]'));
                            if (highlightedElements.length > 0) {
                                highlightedElements[0].click();
                                return true;
                            }
                            return false;
                        }
                    ''')
                    
                    if clicked:
                        print("通过JavaScript成功点击了视频上传元素")
                        try:
                            file_chooser = await self.browser.main_page.wait_for_file_chooser(timeout=5000)
                            await file_chooser.set_files(video_path)
                            print(f"通过点击设置视频文件: {video_path}")
                            await asyncio.sleep(5)
                        except Exception as e:
                            print(f"点击后等待文件选择器失败: {str(e)}")
            
        except Exception as e:
            print(f"上传视频过程中出错: {str(e)}") 