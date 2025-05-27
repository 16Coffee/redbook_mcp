"""
抖音发布服务
"""
import asyncio
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.logging.logger import logger
from src.core.exceptions.exceptions import RedBookMCPException


class DouyinPublishManager:
    """抖音发布管理器"""

    def __init__(self, browser_manager):
        """初始化发布管理器

        Args:
            browser_manager: 抖音浏览器管理器实例
        """
        self.browser = browser_manager

    async def publish_content(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        content_type: str = "auto",
        topics: Optional[List[str]] = None,
        privacy: str = "public",
        allow_comment: bool = True,
        allow_duet: bool = True,
        allow_stitch: bool = True
    ) -> str:
        """发布抖音内容（视频或图文）

        Args:
            title: 标题
            content: 内容描述
            media_paths: 媒体文件路径列表（视频或图片）
            content_type: 内容类型 ("video", "image", "auto")
            topics: 话题标签列表
            privacy: 隐私设置 ("public", "private", "friends")
            allow_comment: 是否允许评论
            allow_duet: 是否允许合拍
            allow_stitch: 是否允许拼接

        Returns:
            发布结果消息
        """
        try:
            # 确保已登录
            if not self.browser.is_logged_in:
                login_result = await self.browser.login()
                if "成功" not in login_result:
                    return f"登录失败: {login_result}"

            # 验证媒体文件
            validated_paths = await self._validate_media_files(media_paths)
            if not validated_paths:
                return "没有有效的媒体文件"

            # 自动检测内容类型
            if content_type == "auto":
                content_type = self._detect_content_type(validated_paths)

            logger.info(f"开始发布抖音{content_type}内容: {title}")

            # 访问创作者中心
            await self._navigate_to_creator_center()

            # 根据内容类型选择发布方式
            if content_type == "video":
                return await self._publish_video(title, content, validated_paths, topics, privacy, allow_comment, allow_duet, allow_stitch)
            elif content_type == "image":
                return await self._publish_image_post(title, content, validated_paths, topics, privacy, allow_comment)
            else:
                return f"不支持的内容类型: {content_type}"

        except Exception as e:
            error_msg = f"发布抖音内容失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _validate_media_files(self, media_paths: List[str]) -> List[str]:
        """验证媒体文件"""
        validated_paths = []

        for path_str in media_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"文件不存在: {path}")
                continue

            # 检查文件大小（抖音限制）
            file_size = path.stat().st_size
            if file_size > 500 * 1024 * 1024:  # 500MB
                logger.warning(f"文件过大: {path} ({file_size / 1024 / 1024:.1f}MB)")
                continue

            # 检查文件格式
            suffix = path.suffix.lower()
            if suffix in ['.mp4', '.mov', '.avi', '.mkv', '.flv']:
                # 视频文件
                validated_paths.append(str(path))
            elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # 图片文件
                validated_paths.append(str(path))
            else:
                logger.warning(f"不支持的文件格式: {path}")

        return validated_paths

    def _detect_content_type(self, media_paths: List[str]) -> str:
        """自动检测内容类型"""
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

        has_video = any(Path(path).suffix.lower() in video_extensions for path in media_paths)
        has_image = any(Path(path).suffix.lower() in image_extensions for path in media_paths)

        if has_video and not has_image:
            return "video"
        elif has_image and not has_video:
            return "image"
        elif has_video and has_image:
            # 如果既有视频又有图片，优先视频
            return "video"
        else:
            return "unknown"

    async def _navigate_to_creator_center(self):
        """导航到创作者中心"""
        try:
            # 访问创作者中心
            creator_url = "https://creator.douyin.com/creator-micro/content/upload"
            await self.browser.goto(creator_url)

            # 等待页面加载
            await asyncio.sleep(3)

            logger.info("已进入抖音创作者中心")

        except Exception as e:
            logger.error(f"导航到创作者中心失败: {str(e)}")
            raise

    async def _publish_video(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        topics: Optional[List[str]],
        privacy: str,
        allow_comment: bool,
        allow_duet: bool,
        allow_stitch: bool
    ) -> str:
        """发布视频"""
        try:
            # 点击发布视频按钮
            await self._click_publish_button("video")

            # 上传视频文件
            video_path = media_paths[0]  # 取第一个视频文件
            await self._upload_video_file(video_path)

            # 等待视频处理
            await self._wait_for_video_processing()

            # 填写视频信息
            await self._fill_video_info(title, content, topics)

            # 设置隐私和互动选项
            await self._set_video_settings(privacy, allow_comment, allow_duet, allow_stitch)

            # 发布视频
            await self._submit_video()

            return f"抖音视频发布成功: {title}"

        except Exception as e:
            logger.error(f"发布视频失败: {str(e)}")
            raise

    async def _publish_image_post(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        topics: Optional[List[str]],
        privacy: str,
        allow_comment: bool
    ) -> str:
        """发布图文"""
        try:
            # 点击发布图文按钮
            await self._click_publish_button("image")

            # 上传图片文件
            await self._upload_image_files(media_paths)

            # 填写图文信息
            await self._fill_image_post_info(title, content, topics)

            # 设置隐私和评论选项
            await self._set_image_post_settings(privacy, allow_comment)

            # 发布图文
            await self._submit_image_post()

            return f"抖音图文发布成功: {title}"

        except Exception as e:
            logger.error(f"发布图文失败: {str(e)}")
            raise

    async def _click_publish_button(self, content_type: str):
        """点击发布按钮"""
        try:
            if content_type == "video":
                # 点击发布视频按钮
                selectors = [
                    'text="发布视频"',
                    '[data-e2e="publish-video"]',
                    '.publish-video-btn'
                ]
            else:
                # 点击发布图文按钮
                selectors = [
                    'text="发布图文"',
                    '[data-e2e="publish-image"]',
                    '.publish-image-btn'
                ]

            for selector in selectors:
                try:
                    element = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        logger.info(f"点击{content_type}发布按钮成功")
                        return
                except Exception:
                    continue

            # 如果没有找到特定按钮，尝试通用上传按钮
            upload_selectors = [
                'text="上传视频"',
                'text="点击上传"',
                '.upload-btn',
                '[data-e2e="upload"]'
            ]

            for selector in upload_selectors:
                try:
                    element = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        logger.info("点击上传按钮成功")
                        return
                except Exception:
                    continue

            raise Exception("未找到发布按钮")

        except Exception as e:
            logger.error(f"点击发布按钮失败: {str(e)}")
            raise

    async def _upload_video_file(self, video_path: str):
        """上传视频文件"""
        try:
            # 查找文件上传输入框（包括隐藏的input元素）
            file_input_selectors = [
                'input[type="file"]',
                'input[accept*="video"]',
                'input[accept*=".mp4"]',
                'input[accept*=".mov"]',
                '[data-e2e="upload-input"]',
                '.upload-input',
                'input[multiple]'
            ]

            file_input = None
            for selector in file_input_selectors:
                try:
                    # 查找所有匹配的input元素，包括隐藏的
                    inputs = await self.browser.main_page.query_selector_all(selector)
                    for input_elem in inputs:
                        # 检查元素是否可用于文件上传
                        try:
                            input_type = await input_elem.get_attribute('type')
                            if input_type == 'file':
                                file_input = input_elem
                                logger.info(f"找到文件上传输入框: {selector}")
                                break
                        except Exception:
                            continue
                    if file_input:
                        break
                except Exception:
                    continue

            if not file_input:
                # 尝试点击上传区域来触发文件选择
                upload_area_selectors = [
                    'text="点击上传或直接拖拽视频文件至此区域"',
                    'text="上传视频"',
                    '.upload-area',
                    '.upload-zone',
                    '[data-e2e="upload-area"]'
                ]

                for selector in upload_area_selectors:
                    try:
                        upload_area = await self.browser.main_page.wait_for_selector(selector, timeout=3000)
                        if upload_area:
                            await upload_area.click()
                            await asyncio.sleep(1)

                            # 再次查找文件输入框
                            file_input = await self.browser.main_page.query_selector('input[type="file"]')
                            if file_input:
                                logger.info(f"通过点击上传区域找到文件输入框: {selector}")
                                break
                    except Exception:
                        continue

            if not file_input:
                # 最后尝试：调试页面元素
                await self._debug_page_elements()
                raise Exception("未找到文件上传输入框")

            # 上传文件
            await file_input.set_input_files(video_path)
            logger.info(f"视频文件上传成功: {video_path}")

            # 等待上传完成
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"上传视频文件失败: {str(e)}")
            raise

    async def _upload_image_files(self, image_paths: List[str]):
        """上传图片文件"""
        try:
            # 查找文件上传输入框（包括隐藏的input元素）
            file_input_selectors = [
                'input[type="file"]',
                'input[accept*="image"]',
                'input[accept*=".jpg"]',
                'input[accept*=".png"]',
                '[data-e2e="upload-input"]',
                '.upload-input',
                'input[multiple]'
            ]

            file_input = None
            for selector in file_input_selectors:
                try:
                    # 查找所有匹配的input元素，包括隐藏的
                    inputs = await self.browser.main_page.query_selector_all(selector)
                    for input_elem in inputs:
                        # 检查元素是否可用于文件上传
                        try:
                            input_type = await input_elem.get_attribute('type')
                            if input_type == 'file':
                                file_input = input_elem
                                logger.info(f"找到文件上传输入框: {selector}")
                                break
                        except Exception:
                            continue
                    if file_input:
                        break
                except Exception:
                    continue

            if not file_input:
                # 尝试点击上传区域来触发文件选择
                upload_area_selectors = [
                    'text="点击上传或直接拖拽图片文件至此区域"',
                    'text="上传图片"',
                    'text="选择图片"',
                    '.upload-area',
                    '.upload-zone',
                    '[data-e2e="upload-area"]'
                ]

                for selector in upload_area_selectors:
                    try:
                        upload_area = await self.browser.main_page.wait_for_selector(selector, timeout=3000)
                        if upload_area:
                            await upload_area.click()
                            await asyncio.sleep(1)

                            # 再次查找文件输入框
                            file_input = await self.browser.main_page.query_selector('input[type="file"]')
                            if file_input:
                                logger.info(f"通过点击上传区域找到文件输入框: {selector}")
                                break
                    except Exception:
                        continue

            if not file_input:
                # 最后尝试：调试页面元素
                await self._debug_page_elements()
                raise Exception("未找到文件上传输入框")

            # 上传所有图片文件
            await file_input.set_input_files(image_paths)
            logger.info(f"图片文件上传成功: {len(image_paths)} 个文件")

            # 等待上传完成
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"上传图片文件失败: {str(e)}")
            raise

    async def _wait_for_video_processing(self):
        """等待视频处理完成"""
        try:
            # 等待视频处理完成的指示器消失
            processing_selectors = [
                '.processing',
                '.uploading',
                'text="处理中"',
                'text="上传中"'
            ]

            max_wait_time = 300  # 最多等待5分钟
            wait_interval = 5
            waited_time = 0

            while waited_time < max_wait_time:
                processing = False
                for selector in processing_selectors:
                    try:
                        element = await self.browser.main_page.query_selector(selector)
                        if element:
                            processing = True
                            break
                    except Exception:
                        continue

                if not processing:
                    logger.info("视频处理完成")
                    return

                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
                logger.info(f"等待视频处理中... ({waited_time}/{max_wait_time}秒)")

            logger.warning("视频处理等待超时，继续执行")

        except Exception as e:
            logger.warning(f"等待视频处理时出错: {str(e)}")

    async def _fill_video_info(self, title: str, content: str, topics: Optional[List[str]]):
        """填写视频信息"""
        try:
            # 填写标题
            await self._fill_title(title)

            # 填写描述
            await self._fill_description(content, topics)

            logger.info("视频信息填写完成")

        except Exception as e:
            logger.error(f"填写视频信息失败: {str(e)}")
            raise

    async def _fill_image_post_info(self, title: str, content: str, topics: Optional[List[str]]):
        """填写图文信息"""
        try:
            # 填写标题
            await self._fill_title(title)

            # 填写描述
            await self._fill_description(content, topics)

            logger.info("图文信息填写完成")

        except Exception as e:
            logger.error(f"填写图文信息失败: {str(e)}")
            raise

    async def _fill_title(self, title: str):
        """填写标题"""
        try:
            title_selectors = [
                'input[placeholder*="标题"]',
                'input[placeholder*="title"]',
                '[data-e2e="title-input"]',
                '.title-input'
            ]

            for selector in title_selectors:
                try:
                    title_input = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if title_input:
                        await title_input.clear()
                        await title_input.fill(title)
                        logger.info(f"标题填写成功: {title}")
                        return
                except Exception:
                    continue

            logger.warning("未找到标题输入框")

        except Exception as e:
            logger.error(f"填写标题失败: {str(e)}")
            raise

    async def _fill_description(self, content: str, topics: Optional[List[str]]):
        """填写描述"""
        try:
            # 构建完整描述
            full_description = content

            # 添加话题标签
            if topics:
                topic_tags = " ".join([f"#{topic}" for topic in topics])
                full_description = f"{content}\n\n{topic_tags}"

            # 查找描述输入框
            desc_selectors = [
                'textarea[placeholder*="描述"]',
                'textarea[placeholder*="说点什么"]',
                '[data-e2e="desc-input"]',
                '.desc-input',
                'textarea'
            ]

            for selector in desc_selectors:
                try:
                    desc_input = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if desc_input:
                        await desc_input.clear()
                        await desc_input.fill(full_description)
                        logger.info("描述填写成功")
                        return
                except Exception:
                    continue

            logger.warning("未找到描述输入框")

        except Exception as e:
            logger.error(f"填写描述失败: {str(e)}")
            raise

    async def _set_video_settings(self, privacy: str, allow_comment: bool, allow_duet: bool, allow_stitch: bool):
        """设置视频选项"""
        try:
            # 设置隐私
            await self._set_privacy(privacy)

            # 设置评论权限
            await self._set_comment_permission(allow_comment)

            # 设置合拍权限
            await self._set_duet_permission(allow_duet)

            # 设置拼接权限
            await self._set_stitch_permission(allow_stitch)

            logger.info("视频设置完成")

        except Exception as e:
            logger.error(f"设置视频选项失败: {str(e)}")
            raise

    async def _set_image_post_settings(self, privacy: str, allow_comment: bool):
        """设置图文选项"""
        try:
            # 设置隐私
            await self._set_privacy(privacy)

            # 设置评论权限
            await self._set_comment_permission(allow_comment)

            logger.info("图文设置完成")

        except Exception as e:
            logger.error(f"设置图文选项失败: {str(e)}")
            raise

    async def _set_privacy(self, privacy: str):
        """设置隐私选项"""
        try:
            privacy_map = {
                "public": ["公开", "所有人可见"],
                "private": ["私密", "仅自己可见"],
                "friends": ["朋友", "朋友可见"]
            }

            privacy_texts = privacy_map.get(privacy, privacy_map["public"])

            for text in privacy_texts:
                try:
                    privacy_element = await self.browser.main_page.wait_for_selector(f'text="{text}"', timeout=3000)
                    if privacy_element:
                        await privacy_element.click()
                        logger.info(f"隐私设置成功: {text}")
                        return
                except Exception:
                    continue

            logger.warning(f"未找到隐私选项: {privacy}")

        except Exception as e:
            logger.warning(f"设置隐私失败: {str(e)}")

    async def _set_comment_permission(self, allow_comment: bool):
        """设置评论权限"""
        try:
            comment_selectors = [
                '[data-e2e="comment-switch"]',
                'text="允许评论"',
                'text="评论"'
            ]

            for selector in comment_selectors:
                try:
                    comment_element = await self.browser.main_page.wait_for_selector(selector, timeout=3000)
                    if comment_element:
                        # 检查当前状态
                        is_checked = await comment_element.is_checked() if hasattr(comment_element, 'is_checked') else None

                        # 如果状态不匹配，点击切换
                        if is_checked is not None and is_checked != allow_comment:
                            await comment_element.click()
                        elif is_checked is None:
                            # 如果无法检查状态，直接点击
                            await comment_element.click()

                        logger.info(f"评论权限设置: {allow_comment}")
                        return
                except Exception:
                    continue

            logger.warning("未找到评论权限设置")

        except Exception as e:
            logger.warning(f"设置评论权限失败: {str(e)}")

    async def _set_duet_permission(self, allow_duet: bool):
        """设置合拍权限"""
        try:
            duet_selectors = [
                '[data-e2e="duet-switch"]',
                'text="允许合拍"',
                'text="合拍"'
            ]

            for selector in duet_selectors:
                try:
                    duet_element = await self.browser.main_page.wait_for_selector(selector, timeout=3000)
                    if duet_element:
                        is_checked = await duet_element.is_checked() if hasattr(duet_element, 'is_checked') else None

                        if is_checked is not None and is_checked != allow_duet:
                            await duet_element.click()
                        elif is_checked is None:
                            await duet_element.click()

                        logger.info(f"合拍权限设置: {allow_duet}")
                        return
                except Exception:
                    continue

            logger.warning("未找到合拍权限设置")

        except Exception as e:
            logger.warning(f"设置合拍权限失败: {str(e)}")

    async def _set_stitch_permission(self, allow_stitch: bool):
        """设置拼接权限"""
        try:
            stitch_selectors = [
                '[data-e2e="stitch-switch"]',
                'text="允许拼接"',
                'text="拼接"'
            ]

            for selector in stitch_selectors:
                try:
                    stitch_element = await self.browser.main_page.wait_for_selector(selector, timeout=3000)
                    if stitch_element:
                        is_checked = await stitch_element.is_checked() if hasattr(stitch_element, 'is_checked') else None

                        if is_checked is not None and is_checked != allow_stitch:
                            await stitch_element.click()
                        elif is_checked is None:
                            await stitch_element.click()

                        logger.info(f"拼接权限设置: {allow_stitch}")
                        return
                except Exception:
                    continue

            logger.warning("未找到拼接权限设置")

        except Exception as e:
            logger.warning(f"设置拼接权限失败: {str(e)}")

    async def _submit_video(self):
        """提交发布视频"""
        try:
            submit_selectors = [
                'text="发布"',
                'text="立即发布"',
                '[data-e2e="publish-btn"]',
                '.publish-btn'
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if submit_btn:
                        await submit_btn.click()
                        logger.info("视频发布提交成功")

                        # 等待发布完成
                        await asyncio.sleep(5)
                        return
                except Exception:
                    continue

            raise Exception("未找到发布按钮")

        except Exception as e:
            logger.error(f"提交视频发布失败: {str(e)}")
            raise

    async def _submit_image_post(self):
        """提交发布图文"""
        try:
            submit_selectors = [
                'text="发布"',
                'text="立即发布"',
                '[data-e2e="publish-btn"]',
                '.publish-btn'
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = await self.browser.main_page.wait_for_selector(selector, timeout=5000)
                    if submit_btn:
                        await submit_btn.click()
                        logger.info("图文发布提交成功")

                        # 等待发布完成
                        await asyncio.sleep(5)
                        return
                except Exception:
                    continue

            raise Exception("未找到发布按钮")

        except Exception as e:
            logger.error(f"提交图文发布失败: {str(e)}")
            raise

    async def _debug_page_elements(self):
        """调试页面元素，帮助找到正确的选择器"""
        try:
            logger.info("开始调试页面元素...")

            # 获取页面URL
            current_url = self.browser.main_page.url
            logger.info(f"当前页面URL: {current_url}")

            # 查找所有input元素
            all_inputs = await self.browser.main_page.query_selector_all('input')
            logger.info(f"页面中共找到 {len(all_inputs)} 个input元素")

            for i, input_elem in enumerate(all_inputs):
                try:
                    input_type = await input_elem.get_attribute('type')
                    input_accept = await input_elem.get_attribute('accept')
                    input_class = await input_elem.get_attribute('class')
                    input_id = await input_elem.get_attribute('id')
                    input_name = await input_elem.get_attribute('name')

                    logger.info(f"Input {i+1}: type={input_type}, accept={input_accept}, class={input_class}, id={input_id}, name={input_name}")
                except Exception as e:
                    logger.warning(f"无法获取input {i+1}的属性: {str(e)}")

            # 查找包含"上传"文字的元素
            upload_texts = ['上传', '选择', '拖拽', 'upload', 'select', 'drag']
            for text in upload_texts:
                try:
                    elements = await self.browser.main_page.query_selector_all(f'text="{text}"')
                    if elements:
                        logger.info(f"找到包含'{text}'的元素: {len(elements)}个")
                except Exception:
                    continue

            # 查找可能的上传区域
            upload_selectors = [
                '.upload',
                '.file-upload',
                '.drop-zone',
                '.upload-area',
                '[data-testid*="upload"]',
                '[class*="upload"]'
            ]

            for selector in upload_selectors:
                try:
                    elements = await self.browser.main_page.query_selector_all(selector)
                    if elements:
                        logger.info(f"找到选择器'{selector}'的元素: {len(elements)}个")
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"调试页面元素失败: {str(e)}")
