#!/usr/bin/env python3
"""
分步骤诊断工具 - 精确定位post_comment超时的具体步骤
"""

import asyncio
import sys
import os
import time

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.infrastructure.browser.browser import BrowserManager

async def step_by_step_diagnosis(url, comment):
    """分步骤诊断post_comment流程，找出超时的具体步骤"""

    print("🔬 分步骤诊断开始...")
    print(f"目标URL: {url}")
    print(f"评论内容: {comment}")

    browser_manager = BrowserManager()

    try:
        # 步骤1: 浏览器启动
        step_start = time.time()
        print("\n📍 步骤1: 浏览器启动...")
        await browser_manager.ensure_browser()
        step_time = time.time() - step_start
        print(f"✅ 步骤1完成 - 耗时: {step_time:.2f}秒")

        # 步骤2: 页面访问
        step_start = time.time()
        print("\n📍 步骤2: 访问页面...")
        await browser_manager.main_page.goto(url, timeout=30000)
        step_time = time.time() - step_start
        print(f"✅ 步骤2完成 - 耗时: {step_time:.2f}秒")

        # 步骤3: 页面加载等待
        step_start = time.time()
        print("\n📍 步骤3: 等待页面加载...")
        await asyncio.sleep(2)
        step_time = time.time() - step_start
        print(f"✅ 步骤3完成 - 耗时: {step_time:.2f}秒")

        # 步骤4: 滚动到底部
        step_start = time.time()
        print("\n📍 步骤4: 滚动到页面底部...")
        await browser_manager.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        step_time = time.time() - step_start
        print(f"✅ 步骤4完成 - 耗时: {step_time:.2f}秒")

        # 步骤5: 滚动后等待
        step_start = time.time()
        print("\n📍 步骤5: 滚动后等待...")
        await asyncio.sleep(1)
        step_time = time.time() - step_start
        print(f"✅ 步骤5完成 - 耗时: {step_time:.2f}秒")

        # 步骤6: 查找评论输入框
        step_start = time.time()
        print("\n📍 步骤6: 查找评论输入框...")
        comment_input = None

        # 6.1: 尝试第一个选择器
        try:
            print("  6.1: 尝试 #content-textarea...")
            comment_input = await browser_manager.main_page.query_selector('#content-textarea')
            if comment_input and await comment_input.is_visible():
                print("  ✅ 6.1: 成功找到")
            else:
                comment_input = None
                print("  ❌ 6.1: 失败")
        except Exception as e:
            print(f"  ❌ 6.1: 异常 - {str(e)}")

        # 6.2: 尝试第二个选择器
        if not comment_input:
            try:
                print("  6.2: 尝试 .content-input...")
                comment_input = await browser_manager.main_page.query_selector('.content-input')
                if comment_input and await comment_input.is_visible():
                    print("  ✅ 6.2: 成功找到")
                else:
                    comment_input = None
                    print("  ❌ 6.2: 失败")
            except Exception as e:
                print(f"  ❌ 6.2: 异常 - {str(e)}")

        # 6.3: 尝试第三个选择器
        if not comment_input:
            try:
                print("  6.3: 尝试属性选择器...")
                comment_input = await browser_manager.main_page.query_selector('p[contenteditable="true"][data-tribute="true"]')
                if comment_input and await comment_input.is_visible():
                    print("  ✅ 6.3: 成功找到")
                else:
                    comment_input = None
                    print("  ❌ 6.3: 失败")
            except Exception as e:
                print(f"  ❌ 6.3: 异常 - {str(e)}")

        step_time = time.time() - step_start
        print(f"✅ 步骤6完成 - 耗时: {step_time:.2f}秒")

        if not comment_input:
            print("❌ 未找到评论输入框，诊断结束")
            return

        # 步骤7: 滚动到元素
        step_start = time.time()
        print("\n📍 步骤7: 滚动到输入框...")
        await comment_input.scroll_into_view_if_needed()
        step_time = time.time() - step_start
        print(f"✅ 步骤7完成 - 耗时: {step_time:.2f}秒")

        # 步骤8: 等待
        step_start = time.time()
        print("\n📍 步骤8: 等待0.3秒...")
        await asyncio.sleep(0.3)
        step_time = time.time() - step_start
        print(f"✅ 步骤8完成 - 耗时: {step_time:.2f}秒")

        # 步骤9: 激活输入框（使用修复后的方法）
        step_start = time.time()
        print("\n📍 步骤9: 激活输入框...")

        # 方法1: 先尝试点击覆盖的"评论"元素来激活输入框
        try:
            print("  9.1: 尝试点击覆盖的'评论'元素...")
            overlay_element = await browser_manager.main_page.query_selector('span:has-text("评论")')
            if overlay_element:
                await overlay_element.click()
                await asyncio.sleep(0.5)
                print("  ✅ 9.1: 成功点击覆盖元素")
            else:
                print("  ❌ 9.1: 未找到覆盖元素")
        except Exception as e:
            print(f"  ❌ 9.1: 异常 - {str(e)}")

        # 方法2: 使用JavaScript直接聚焦输入框
        try:
            print("  9.2: 使用JavaScript聚焦输入框...")
            await browser_manager.main_page.evaluate('''
                () => {
                    const textarea = document.querySelector('#content-textarea');
                    if (textarea) {
                        textarea.focus();
                        textarea.click();
                    }
                }
            ''')
            await asyncio.sleep(0.3)
            print("  ✅ 9.2: JavaScript聚焦完成")
        except Exception as e:
            print(f"  ❌ 9.2: 异常 - {str(e)}")

        # 方法3: 如果还不行，使用force点击
        try:
            print("  9.3: 尝试force点击...")
            await comment_input.click(force=True)
            await asyncio.sleep(0.3)
            print("  ✅ 9.3: force点击完成")
        except Exception as e:
            print(f"  ❌ 9.3: 异常 - {str(e)}")

        step_time = time.time() - step_start
        print(f"✅ 步骤9完成 - 耗时: {step_time:.2f}秒")

        # 步骤10: 全选内容
        step_start = time.time()
        print("\n📍 步骤10: 全选内容...")
        await browser_manager.main_page.keyboard.press("Control+a")
        step_time = time.time() - step_start
        print(f"✅ 步骤10完成 - 耗时: {step_time:.2f}秒")

        # 步骤11: 输入评论
        step_start = time.time()
        print("\n📍 步骤11: 输入评论内容...")
        await browser_manager.main_page.keyboard.type(comment)
        step_time = time.time() - step_start
        print(f"✅ 步骤11完成 - 耗时: {step_time:.2f}秒")

        # 步骤12: 等待
        step_start = time.time()
        print("\n📍 步骤12: 等待0.3秒...")
        await asyncio.sleep(0.3)
        step_time = time.time() - step_start
        print(f"✅ 步骤12完成 - 耗时: {step_time:.2f}秒")

        # 步骤13: 按Enter发送
        step_start = time.time()
        print("\n📍 步骤13: 按Enter发送...")
        await browser_manager.main_page.keyboard.press("Enter")
        step_time = time.time() - step_start
        print(f"✅ 步骤13完成 - 耗时: {step_time:.2f}秒")

        # 步骤14: 最后等待
        step_start = time.time()
        print("\n📍 步骤14: 最后等待1秒...")
        await asyncio.sleep(1)
        step_time = time.time() - step_start
        print(f"✅ 步骤14完成 - 耗时: {step_time:.2f}秒")

        print("\n🎯 所有步骤完成！")

        # 检查是否成功发送
        print("\n🔍 检查发送结果...")
        result = await browser_manager.main_page.evaluate('''
            () => {
                const textarea = document.querySelector('#content-textarea');
                return {
                    textareaContent: textarea ? textarea.textContent : 'not found',
                    textareaValue: textarea ? textarea.value : 'not found',
                    textareaInnerText: textarea ? textarea.innerText : 'not found'
                };
            }
        ''')
        print(f"输入框状态: {result}")

    except Exception as e:
        print(f"❌ 诊断过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            await browser_manager.close()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python debug_step_by_step.py <URL> <评论内容>")
        print("例如: python debug_step_by_step.py 'https://www.xiaohongshu.com/explore/xxx' '测试评论'")
        sys.exit(1)

    url = sys.argv[1]
    comment = sys.argv[2]

    asyncio.run(step_by_step_diagnosis(url, comment))
