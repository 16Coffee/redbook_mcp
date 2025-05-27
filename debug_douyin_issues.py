#!/usr/bin/env python3
"""
抖音问题诊断脚本
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def debug_login_issue():
    """诊断登录问题"""
    print("🔍 诊断登录问题...")

    try:
        from src.infrastructure.browser.douyin_browser import DouyinBrowserManager
        from src.infrastructure.browser.douyin_login_manager import DouyinLoginManager

        browser_manager = DouyinBrowserManager()
        login_manager = DouyinLoginManager(browser_manager)

        # 1. 检查登录状态文件
        print(f"登录状态文件存在: {login_manager.login_state_file.exists()}")
        if login_manager.login_state_file.exists():
            with open(login_manager.login_state_file, 'r', encoding='utf-8') as f:
                import json
                state_data = json.load(f)
                print(f"登录状态文件内容: {state_data}")

        # 2. 启动浏览器并检查状态
        await browser_manager.ensure_browser()
        print(f"浏览器启动成功，当前URL: {browser_manager.main_page.url}")

        # 3. 检查登录状态
        is_logged_in = await login_manager.check_login_status(force_check=True)
        print(f"登录状态检查结果: {is_logged_in}")

        # 4. 分析页面元素
        print("\n分析页面元素...")

        # 查找登录相关元素
        login_elements = await browser_manager.main_page.query_selector_all('text="登录"')
        print(f"找到'登录'元素: {len(login_elements)}个")

        creator_elements = await browser_manager.main_page.query_selector_all('text="我是创作者"')
        print(f"找到'我是创作者'元素: {len(creator_elements)}个")

        # 5. 获取会话信息
        session_info = login_manager.get_session_info()
        print(f"\n会话信息:")
        for key, value in session_info.items():
            print(f"  {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ 登录诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def debug_publish_flow():
    """诊断发布流程"""
    print("\n🔍 诊断发布流程...")

    try:
        from src.domain.services.douyin_publish import DouyinPublishManager
        from src.infrastructure.browser.douyin_browser import DouyinBrowserManager

        browser_manager = DouyinBrowserManager()
        publish_manager = DouyinPublishManager(browser_manager)

        # 确保浏览器启动
        await browser_manager.ensure_browser()

        # 1. 尝试导航到创作者中心
        print("导航到创作者中心...")
        await browser_manager.goto("https://creator.douyin.com")
        await asyncio.sleep(3)

        current_url = browser_manager.main_page.url
        print(f"当前URL: {current_url}")

        # 2. 查找发布相关按钮
        print("\n查找发布相关按钮...")

        publish_selectors = [
            'text="发布视频"',
            'text="发布图文"',
            'text="上传视频"',
            'text="创作"',
            'text="发布"',
            '.publish-btn',
            '[data-e2e="publish"]',
            'a[href*="upload"]',
            'button[class*="upload"]'
        ]

        for selector in publish_selectors:
            try:
                elements = await browser_manager.main_page.query_selector_all(selector)
                if elements:
                    print(f"  找到选择器'{selector}': {len(elements)}个元素")
                    for i, elem in enumerate(elements):
                        try:
                            text = await elem.inner_text()
                            href = await elem.get_attribute('href')
                            class_name = await elem.get_attribute('class')
                            print(f"    元素{i+1}: text='{text}', href='{href}', class='{class_name}'")
                        except Exception:
                            pass
            except Exception:
                continue

        # 3. 查找导航菜单
        print("\n查找导航菜单...")
        nav_selectors = [
            'nav',
            '.nav',
            '.menu',
            '.sidebar',
            'ul',
            '[role="navigation"]'
        ]

        for selector in nav_selectors:
            try:
                elements = await browser_manager.main_page.query_selector_all(selector)
                if elements:
                    print(f"  找到导航选择器'{selector}': {len(elements)}个元素")
            except Exception:
                continue

        # 4. 尝试调试页面元素
        await publish_manager._debug_page_elements()

        return True

    except Exception as e:
        print(f"❌ 发布流程诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_manual_login():
    """测试手动登录流程"""
    print("\n🔍 测试手动登录流程...")

    try:
        from src.infrastructure.browser.douyin_login_manager import DouyinLoginManager
        from src.infrastructure.browser.douyin_browser import DouyinBrowserManager

        browser_manager = DouyinBrowserManager()
        login_manager = DouyinLoginManager(browser_manager)

        # 清除现有登录状态
        await login_manager.clear_login_state()
        print("已清除现有登录状态")

        # 启动登录流程
        print("开始手动登录流程...")
        print("请在浏览器中完成登录，脚本将等待...")

        success = await login_manager.login()

        if success:
            print("✅ 登录成功")

            # 保存登录状态
            await login_manager.save_login_state()
            print("✅ 登录状态已保存")

            # 验证登录状态
            is_logged_in = await login_manager.check_login_status(force_check=True)
            print(f"登录状态验证: {is_logged_in}")

        else:
            print("❌ 登录失败")

        return success

    except Exception as e:
        print(f"❌ 手动登录测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_publish():
    """测试简单发布流程"""
    print("\n🔍 测试简单发布流程...")

    try:
        from src.interfaces.mcp.server import publish_douyin_content

        # 创建测试视频文件
        test_dir = Path("test_media")
        test_dir.mkdir(exist_ok=True)

        test_video = test_dir / "test_video.mp4"
        # 创建一个小的测试文件（1KB）
        test_video.write_bytes(b"fake video data for testing" * 50)

        print(f"✅ 创建测试文件: {test_video}")
        print(f"文件大小: {test_video.stat().st_size} bytes")

        # 测试发布
        print("\n🚀 开始测试发布...")
        result = await publish_douyin_content(
            title="测试修复后的发布",
            content="测试抖音发布功能修复",
            media_paths=[str(test_video)],
            content_type="video"
        )

        print(f"📋 发布结果: {result}")

        # 清理测试文件
        test_video.unlink()
        test_dir.rmdir()
        print("✅ 测试文件清理完成")

        return "成功" in result

    except Exception as e:
        print(f"❌ 发布测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主诊断函数"""
    print("🚀 开始抖音问题诊断...\n")

    tests = [
        ("登录问题诊断", debug_login_issue),
        ("发布流程诊断", debug_publish_flow),
        ("手动登录测试", test_manual_login),
        ("简单发布测试", test_simple_publish)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")

        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 出现异常: {str(e)}")
            results.append((test_name, False))

        print()

        # 在手动登录测试后暂停，让用户完成登录
        if test_name == "手动登录测试":
            input("按回车键继续下一个测试...")

    # 总结
    print(f"{'='*60}")
    print("诊断总结")
    print(f"{'='*60}")

    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print("\n📋 建议修复方案:")
    print("1. 检查登录状态保存和恢复机制")
    print("2. 更新发布页面导航逻辑")
    print("3. 完善页面元素选择器")
    print("4. 增强错误处理和重试机制")

if __name__ == "__main__":
    asyncio.run(main())
