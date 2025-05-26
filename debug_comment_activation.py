#!/usr/bin/env python3
"""
评论输入框激活状态诊断工具
验证每个步骤是否真正成功
"""

import asyncio
import sys
import os
import time

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.infrastructure.browser.browser import BrowserManager

async def detailed_comment_activation_diagnosis(url, comment):
    """详细诊断评论输入框激活状态"""

    print("🔬 详细评论激活诊断开始...")
    print(f"目标URL: {url}")
    print(f"评论内容: {comment}")

    browser_manager = BrowserManager()

    try:
        # 步骤1: 浏览器启动
        print("\n📍 步骤1: 浏览器启动...")
        await browser_manager.ensure_browser()
        print("✅ 浏览器启动成功")

        # 步骤2: 页面访问
        print("\n📍 步骤2: 访问页面...")
        await browser_manager.main_page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        print("✅ 页面访问成功")

        # 步骤3: 滚动到底部
        print("\n📍 步骤3: 滚动到页面底部...")
        await browser_manager.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        print("✅ 滚动完成")

        # 步骤4: 检查输入框初始状态
        print("\n📍 步骤4: 检查输入框初始状态...")
        initial_state = await browser_manager.main_page.evaluate('''
            () => {
                const textarea = document.querySelector('#content-textarea');
                if (!textarea) return {found: false};

                const rect = textarea.getBoundingClientRect();
                const style = getComputedStyle(textarea);

                return {
                    found: true,
                    visible: textarea.offsetParent !== null,
                    focused: document.activeElement === textarea,
                    editable: textarea.contentEditable,
                    textContent: textarea.textContent,
                    value: textarea.value || '',
                    rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                    style: {
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        pointerEvents: style.pointerEvents
                    },
                    classList: Array.from(textarea.classList),
                    attributes: {
                        id: textarea.id,
                        class: textarea.className,
                        contenteditable: textarea.contentEditable,
                        'data-tribute': textarea.getAttribute('data-tribute')
                    }
                };
            }
        ''')
        print(f"📊 输入框初始状态: {initial_state}")

        if not initial_state['found']:
            print("❌ 未找到输入框，诊断结束")
            return

        # 步骤5: 检查覆盖元素
        print("\n📍 步骤5: 检查覆盖元素...")
        overlay_info = await browser_manager.main_page.evaluate('''
            () => {
                const overlays = Array.from(document.querySelectorAll('span')).filter(span =>
                    span.textContent && span.textContent.includes('评论')
                );

                return overlays.map(overlay => {
                    const rect = overlay.getBoundingClientRect();
                    return {
                        text: overlay.textContent,
                        visible: overlay.offsetParent !== null,
                        rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                        className: overlay.className,
                        parent: overlay.parentElement ? overlay.parentElement.className : 'no parent'
                    };
                });
            }
        ''')
        print(f"📊 覆盖元素信息: {overlay_info}")

        # 步骤6: 尝试点击覆盖元素
        print("\n📍 步骤6: 尝试点击覆盖元素...")
        try:
            overlay_element = await browser_manager.main_page.query_selector('span:has-text("评论")')
            if overlay_element:
                print("🎯 找到覆盖元素，尝试点击...")
                await overlay_element.click()
                await asyncio.sleep(0.5)
                print("✅ 覆盖元素点击完成")
            else:
                print("❌ 未找到覆盖元素")
        except Exception as e:
            print(f"❌ 点击覆盖元素失败: {str(e)}")

        # 步骤7: 检查点击后的输入框状态
        print("\n📍 步骤7: 检查点击后的输入框状态...")
        after_click_state = await browser_manager.main_page.evaluate('''
            () => {
                const textarea = document.querySelector('#content-textarea');
                if (!textarea) return {found: false};

                const rect = textarea.getBoundingClientRect();
                const style = getComputedStyle(textarea);

                return {
                    found: true,
                    visible: textarea.offsetParent !== null,
                    focused: document.activeElement === textarea,
                    editable: textarea.contentEditable,
                    textContent: textarea.textContent,
                    value: textarea.value || '',
                    rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                    style: {
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        pointerEvents: style.pointerEvents
                    },
                    hasPlaceholder: textarea.getAttribute('placeholder') || textarea.getAttribute('data-placeholder') || 'none'
                };
            }
        ''')
        print(f"📊 点击后输入框状态: {after_click_state}")

        # 步骤8: 尝试JavaScript聚焦
        print("\n📍 步骤8: 尝试JavaScript聚焦...")
        try:
            await browser_manager.main_page.evaluate('''
                () => {
                    const textarea = document.querySelector('#content-textarea');
                    if (textarea) {
                        textarea.focus();
                        textarea.click();
                        // 尝试触发各种事件
                        textarea.dispatchEvent(new Event('focus'));
                        textarea.dispatchEvent(new Event('click'));
                        textarea.dispatchEvent(new Event('mousedown'));
                        textarea.dispatchEvent(new Event('mouseup'));
                    }
                }
            ''')
            await asyncio.sleep(0.3)
            print("✅ JavaScript聚焦完成")
        except Exception as e:
            print(f"❌ JavaScript聚焦失败: {str(e)}")

        # 步骤9: 检查聚焦后的状态
        print("\n📍 步骤9: 检查聚焦后的状态...")
        after_focus_state = await browser_manager.main_page.evaluate('''
            () => {
                const textarea = document.querySelector('#content-textarea');
                if (!textarea) return {found: false};

                return {
                    found: true,
                    focused: document.activeElement === textarea,
                    textContent: textarea.textContent,
                    value: textarea.value || '',
                    canEdit: textarea.isContentEditable,
                    readOnly: textarea.readOnly,
                    disabled: textarea.disabled
                };
            }
        ''')
        print(f"📊 聚焦后状态: {after_focus_state}")

        # 步骤10: 尝试输入测试文本
        print("\n📍 步骤10: 尝试输入测试文本...")
        try:
            # 先清空
            await browser_manager.main_page.keyboard.press("Control+a")
            await asyncio.sleep(0.1)

            # 输入测试文本
            test_text = "测试输入"
            await browser_manager.main_page.keyboard.type(test_text)
            await asyncio.sleep(0.5)
            print(f"✅ 测试文本输入完成: {test_text}")
        except Exception as e:
            print(f"❌ 输入测试文本失败: {str(e)}")

        # 步骤11: 检查输入后的状态
        print("\n📍 步骤11: 检查输入后的状态...")
        after_input_state = await browser_manager.main_page.evaluate('''
            () => {
                const textarea = document.querySelector('#content-textarea');
                if (!textarea) return {found: false};

                return {
                    found: true,
                    textContent: textarea.textContent,
                    value: textarea.value || '',
                    innerHTML: textarea.innerHTML,
                    innerText: textarea.innerText
                };
            }
        ''')
        print(f"📊 输入后状态: {after_input_state}")

        # 步骤12: 检查是否真的可以输入
        if after_input_state['found']:
            has_content = (
                after_input_state['textContent'].strip() != '' or
                after_input_state['value'].strip() != '' or
                after_input_state['innerText'].strip() != ''
            )
            if has_content:
                print("✅ 输入框确实可以输入内容！")

                # 尝试输入实际评论
                print(f"\n📍 步骤13: 输入实际评论: {comment}")
                await browser_manager.main_page.keyboard.press("Control+a")
                await browser_manager.main_page.keyboard.type(comment)
                await asyncio.sleep(0.5)

                # 检查实际评论是否输入成功
                final_state = await browser_manager.main_page.evaluate('''
                    () => {
                        const textarea = document.querySelector('#content-textarea');
                        return textarea ? {
                            textContent: textarea.textContent,
                            value: textarea.value || '',
                            innerText: textarea.innerText
                        } : null;
                    }
                ''')
                print(f"📊 最终输入状态: {final_state}")

                # 尝试发送
                print("\n📍 步骤14: 尝试发送评论...")
                await browser_manager.main_page.keyboard.press("Enter")
                await asyncio.sleep(2)

                # 检查发送后状态
                send_result = await browser_manager.main_page.evaluate('''
                    () => {
                        const textarea = document.querySelector('#content-textarea');
                        return textarea ? {
                            textContent: textarea.textContent,
                            value: textarea.value || '',
                            innerText: textarea.innerText
                        } : null;
                    }
                ''')
                print(f"📊 发送后状态: {send_result}")

                if send_result:
                    has_content = (
                        send_result['textContent'].strip() != '' or
                        send_result['value'].strip() != '' or
                        send_result['innerText'].strip() != ''
                    )
                    if has_content:
                        print("❌ 评论发送失败！输入框仍有内容")
                        print(f"   内容: textContent='{send_result['textContent']}'")
                        print(f"   内容: value='{send_result['value']}'")
                        print(f"   内容: innerText='{send_result['innerText']}'")
                    else:
                        print("🎉 评论发送成功！输入框已清空")
                else:
                    print("❌ 无法检查发送状态")

            else:
                print("❌ 输入框无法输入内容，可能被禁用或有其他问题")

        print("\n🎯 诊断完成！")

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
        print("使用方法: python debug_comment_activation.py <URL> <评论内容>")
        print("例如: python debug_comment_activation.py 'https://www.xiaohongshu.com/explore/xxx' '测试评论'")
        sys.exit(1)

    url = sys.argv[1]
    comment = sys.argv[2]

    asyncio.run(detailed_comment_activation_diagnosis(url, comment))
