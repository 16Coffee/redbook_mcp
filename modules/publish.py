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
    
    async def publish_note(self, title: str, content: str, image_paths: List[str], topics: Optional[List[str]] = None):
        """发布图文笔记
        
        Args:
            title (str): 笔记标题
            content (str): 笔记正文内容
            image_paths (List[str]): 图片路径列表
            topics (Optional[List[str]], optional): 话题标签列表. 默认为None.
        
        Returns:
            str: 操作结果
        """
        login_status = await self.browser.ensure_browser()
        if not login_status:
            return "请先登录小红书账号，才能发布笔记"
        
        try:
            # 访问小红书创作服务平台
            await self.browser.goto("https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch", wait_time=5)
            
            # 切换到图文模式
            try:
                text_tab = await self.browser.main_page.query_selector('text="上传图文"')
                if text_tab:
                    await text_tab.click()
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"切换到图文模式时出错: {str(e)}")
            
            # 上传图片
            for img_path in image_paths:
                try:
                    if not os.path.exists(img_path):
                        print(f"图片不存在: {img_path}")
                        continue
                    
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
                        continue  # 如果成功直接设置文件，跳过后续尝试
                                
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
                        
                        # 保存按钮截图（调试用）
                        try:
                            button_screenshot_path = os.path.join(os.path.dirname(img_path), "button_screenshot.png")
                            await upload_button.screenshot(path=button_screenshot_path)
                            print(f"已保存按钮截图到: {button_screenshot_path}")
                        except Exception as btn_ss_e:
                            print(f"按钮截图失败: {str(btn_ss_e)}")
                        
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
                    else:
                        # 如果找不到红色按钮，尝试使用JavaScript定位元素
                        print("未找到红色上传按钮，尝试使用JavaScript定位")
                        
                        # 使用JavaScript查找可能的上传按钮 - 多种特征匹配
                        js_result = await self.browser.main_page.evaluate('''
                            () => {
                                // 查找包含"上传图片"文本的按钮元素
                                const textElements = Array.from(document.querySelectorAll('button, a, div, span'));
                                const uploadBtn = textElements.find(el => 
                                    el.textContent && 
                                    el.textContent.includes('上传图片')
                                );
                                
                                if (uploadBtn) {
                                    // 高亮并返回元素信息
                                    uploadBtn.style.border = '5px solid green';
                                    return {
                                        found: true,
                                        method: 'text',
                                        tag: uploadBtn.tagName,
                                        text: uploadBtn.textContent.trim(),
                                        classes: uploadBtn.className
                                    };
                                }
                                
                                // 查找红色按钮元素
                                const redButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                                    const style = window.getComputedStyle(btn);
                                    return (
                                        style.backgroundColor.includes('rgb(255') || // 红色背景
                                        style.color.includes('rgb(255, 0, 0)') ||   // 红色文字
                                        btn.className.includes('danger') ||         // 危险按钮类
                                        btn.className.includes('primary') ||        // 主要按钮类
                                        btn.className.includes('upload')            // 上传按钮类
                                    );
                                });
                                
                                if (redButtons.length > 0) {
                                    // 高亮并返回找到的第一个红色按钮
                                    redButtons[0].style.border = '5px solid blue';
                                    return {
                                        found: true, 
                                        method: 'color',
                                        tag: redButtons[0].tagName,
                                        text: redButtons[0].textContent.trim(),
                                        classes: redButtons[0].className
                                    };
                                }
                                
                                // 查找所有上传相关元素
                                const uploadElements = Array.from(document.querySelectorAll('input[type="file"], .upload, [class*="upload"]'));
                                if (uploadElements.length > 0) {
                                    // 高亮并返回找到的第一个上传元素
                                    uploadElements[0].style.border = '5px solid yellow';
                                    return {
                                        found: true,
                                        method: 'upload',
                                        tag: uploadElements[0].tagName,
                                        type: uploadElements[0].type || 'none',
                                        classes: uploadElements[0].className
                                    };
                                }
                                
                                return { found: false };
                            }
                        ''')
                        
                        print(f"JavaScript查找结果: {js_result}")
                        
                        if js_result.get('found'):
                            # 根据JavaScript查找结果尝试点击
                            print(f"JavaScript找到了可能的上传元素: {js_result.get('method')} - {js_result.get('tag')} - {js_result.get('text', '')} - {js_result.get('classes')}")
                            
                            try:
                                # 尝试直接通过JavaScript点击
                                clicked = await self.browser.main_page.evaluate('''
                                    () => {
                                        // 查找已高亮的元素
                                        const highlightedElements = Array.from(document.querySelectorAll('[style*="border: 5px solid"]'));
                                        if (highlightedElements.length > 0) {
                                            // 点击第一个高亮元素
                                            highlightedElements[0].click();
                                            return true;
                                        }
                                        
                                        // 如上传按钮
                                        const uploadButtons = Array.from(document.querySelectorAll('button, a, div, span')).filter(el => 
                                            el.textContent && el.textContent.includes('上传图片')
                                        );
                                        if (uploadButtons.length > 0) {
                                            uploadButtons[0].click();
                                            return true;
                                        }
                                        
                                        // 查找红色按钮
                                        const redButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                                            const style = window.getComputedStyle(btn);
                                            return (
                                                style.backgroundColor.includes('rgb(255') || 
                                                style.color.includes('rgb(255, 0, 0)') ||
                                                btn.className.includes('danger') ||
                                                btn.className.includes('primary') ||
                                                btn.className.includes('upload')
                                            );
                                        });
                                        if (redButtons.length > 0) {
                                            redButtons[0].click();
                                            return true;
                                        }
                                        
                                        return false;
                                    }
                                ''')
                                
                                if clicked:
                                    print("通过JavaScript成功点击了上传元素")
                                    try:
                                        # 等待文件选择器
                                        file_chooser = await self.browser.main_page.wait_for_file_chooser(timeout=5000)
                                        await file_chooser.set_files(img_path)
                                        print(f"通过JavaScript点击后设置文件: {img_path}")
                                        await asyncio.sleep(3)  # 等待图片上传
                                    except Exception as js_fc_e:
                                        print(f"JavaScript点击后等待文件选择器出错: {str(js_fc_e)}")
                                        
                                        # 如果文件选择器没出现，尝试直接查找文件输入
                                        try:
                                            await asyncio.sleep(1)  # 等待可能的DOM变化
                                            file_input = await self.browser.main_page.query_selector('input[type="file"]')
                                            if file_input:
                                                print("JavaScript点击后找到文件输入元素")
                                                await file_input.set_input_files(img_path)
                                                print(f"已设置文件: {img_path}")
                                                await asyncio.sleep(3)  # 等待图片上传
                                        except Exception as js_fi_e:
                                            print(f"JavaScript点击后尝试找文件输入出错: {str(js_fi_e)}")
                                else:
                                    print("JavaScript无法点击任何上传元素")
                            except Exception as js_click_e:
                                print(f"通过JavaScript点击上传元素出错: {str(js_click_e)}")
                        else:
                            print("JavaScript没有找到任何可能的上传元素")
                            
                            # 最后尝试直接找上传区域
                            try:
                                # 根据截图中看到的上传区域，尝试查找并点击
                                upload_area = await self.browser.main_page.query_selector('.upload-area, .el-upload, .upload-container, [class*="upload"]')
                                if upload_area:
                                    print("找到上传区域，尝试点击")
                                    file_chooser_promise = self.browser.main_page.wait_for_file_chooser(timeout=5000)
                                    await upload_area.click()
                                    print("已点击上传区域")
                                    
                                    try:
                                        file_chooser = await file_chooser_promise
                                        await file_chooser.set_files(img_path)
                                        print(f"通过上传区域设置文件: {img_path}")
                                        await asyncio.sleep(3)  # 等待图片上传
                                    except Exception as area_fc_e:
                                        print(f"点击上传区域后等待文件选择器出错: {str(area_fc_e)}")
                                else:
                                    print("未找到任何上传区域")
                            except Exception as area_e:
                                print(f"尝试通过上传区域上传出错: {str(area_e)}")
                except Exception as e:
                    print(f"上传图片过程中出错: {str(e)}")
            
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
                    
                    # 正则提取所有#话题
                    content = content  # 保证变量名一致
                    pattern = r'(#[\u4e00-\u9fa5A-Za-z0-9_]+)'
                    parts = re.split(f'({pattern})', content)
                    
                    for part in parts:
                        if re.match(pattern, part):
                            # 输入#话题
                            await content_input.type(part)
                            await asyncio.sleep(1)  # 等待下拉建议出现
                            # 尝试点击第一个下拉建议项
                            suggestion_selectors = [
                                '.el-select-dropdown__item',
                                '.suggestion-list-item',
                                '.topic-suggestion-item',
                                'li[role="option"]',
                                '.el-autocomplete-suggestion li',
                                '.el-dropdown-menu__item',
                                '.el-select-dropdown li',
                                '.el-dropdown-menu li',
                                '.el-select-dropdown__wrap li',
                                '.el-select-dropdown__list li',
                                '.el-select-dropdown__item span',
                                '.el-select-dropdown__item',
                                '.el-dropdown-menu__item',
                                '.el-dropdown-menu li',
                                '.el-select-dropdown__item',
                                '.el-select-dropdown__item span',
                            ]
                            suggestion_clicked = False
                            for selector in suggestion_selectors:
                                try:
                                    suggestion = await self.browser.main_page.query_selector(selector)
                                    if suggestion and await suggestion.is_visible():
                                        await suggestion.click()
                                        await asyncio.sleep(0.5)
                                        suggestion_clicked = True
                                        break
                                except Exception:
                                    continue
                            if not suggestion_clicked:
                                print(f"未找到下拉建议项，标签 {part} 未被激活")
                        else:
                            # 普通内容直接输入
                            if part:
                                await content_input.type(part)
                                await asyncio.sleep(0.1)
                    await asyncio.sleep(1)
                else:
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
                    await self.browser.main_page.keyboard.type(content)
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"输入正文内容时出错: {str(e)}")
            
            # 添加话题标签
            if topics and len(topics) > 0:
                try:
                    # 点击话题按钮
                    topic_button = await self.browser.main_page.query_selector('text="话题", [aria-label="话题"]')
                    if topic_button:
                        await topic_button.click()
                        await asyncio.sleep(1)
                        
                        # 为每个话题
                        for topic in topics:
                            try:
                                # 搜索话题
                                topic_input = await self.browser.main_page.query_selector('input[placeholder*="搜索"], input[placeholder*="话题"]')
                                if topic_input:
                                    await topic_input.fill(topic)
                                    await asyncio.sleep(1)
                                    
                                    # 选择第一个搜索结果
                                    topic_result = await self.browser.main_page.query_selector('.topic-item, .search-result-item')
                                    if topic_result:
                                        await topic_result.click()
                                        await asyncio.sleep(1)
                                    
                                    # 清空搜索框，准备输入下一个话题
                                    await topic_input.fill("")
                                    await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"添加话题 {topic} 时出错: {str(e)}")
                except Exception as e:
                    print(f"添加话题标签时出错: {str(e)}")
            
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