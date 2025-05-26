#!/usr/bin/env python3
"""
精确定位发送按钮的工具
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.infrastructure.browser.browser import BrowserManager

async def precise_send_button_test(url):
    """精确测试发送按钮定位和点击"""
    
    print("🔍 精确发送按钮测试开始...")
    
    browser_manager = BrowserManager()
    
    try:
        await browser_manager.ensure_browser()
        await browser_manager.main_page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        
        # 滚动到底部
        await browser_manager.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        
        # 激活输入框
        print("📝 激活输入框...")
        overlay_element = await browser_manager.main_page.query_selector('span:has-text("评论")')
        if overlay_element:
            await overlay_element.click()
            await asyncio.sleep(0.5)
        
        # 聚焦输入框
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
        
        # 输入测试文本
        test_comment = "测试发送按钮定位"
        await browser_manager.main_page.keyboard.type(test_comment)
        await asyncio.sleep(0.5)
        print(f"✅ 输入测试文本: {test_comment}")
        
        # 详细分析发送按钮区域
        print("\n🔍 详细分析发送按钮区域...")
        button_analysis = await browser_manager.main_page.evaluate('''
            () => {
                const results = [];
                
                // 1. 查找评论输入框附近的所有元素
                const textarea = document.querySelector('#content-textarea');
                if (!textarea) return {error: '未找到输入框'};
                
                const textareaRect = textarea.getBoundingClientRect();
                
                // 2. 查找输入框附近100px范围内的所有元素
                const allElements = Array.from(document.querySelectorAll('*'));
                const nearbyElements = allElements.filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.x >= textareaRect.x - 100 && 
                           rect.x <= textareaRect.x + textareaRect.width + 100 &&
                           rect.y >= textareaRect.y - 50 &&
                           rect.y <= textareaRect.y + textareaRect.height + 100;
                });
                
                // 3. 分析每个附近的元素
                nearbyElements.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const text = el.textContent ? el.textContent.trim() : '';
                    
                    if (text.includes('发送') || text.includes('取消') || 
                        el.tagName === 'BUTTON' || 
                        el.onclick || 
                        el.style.cursor === 'pointer') {
                        
                        results.push({
                            index: index,
                            tag: el.tagName,
                            text: text,
                            className: el.className,
                            id: el.id,
                            visible: el.offsetParent !== null,
                            rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                            hasOnclick: !!el.onclick,
                            cursor: el.style.cursor,
                            role: el.getAttribute('role'),
                            type: el.getAttribute('type'),
                            innerHTML: el.innerHTML.length > 200 ? el.innerHTML.substring(0, 200) + '...' : el.innerHTML
                        });
                    }
                });
                
                return {
                    textareaRect: textareaRect,
                    nearbyCount: nearbyElements.length,
                    candidates: results
                };
            }
        ''')
        
        print(f"📊 输入框位置: {button_analysis.get('textareaRect')}")
        print(f"📊 附近元素总数: {button_analysis.get('nearbyCount')}")
        print(f"📊 候选发送按钮数量: {len(button_analysis.get('candidates', []))}")
        
        candidates = button_analysis.get('candidates', [])
        for i, candidate in enumerate(candidates):
            print(f"\n候选 {i+1}:")
            print(f"  标签: {candidate['tag']}")
            print(f"  文本: '{candidate['text']}'")
            print(f"  类名: {candidate['className']}")
            print(f"  ID: {candidate['id']}")
            print(f"  可见: {candidate['visible']}")
            print(f"  位置: {candidate['rect']}")
            print(f"  有点击事件: {candidate['hasOnclick']}")
            print(f"  鼠标样式: {candidate['cursor']}")
            print(f"  角色: {candidate['role']}")
            print(f"  类型: {candidate['type']}")
            if len(candidate['innerHTML']) < 100:
                print(f"  HTML: {candidate['innerHTML']}")
        
        # 尝试多种点击方式
        print(f"\n🎯 尝试多种发送方式...")
        
        # 方式1: 通过坐标点击
        send_candidates = [c for c in candidates if '发送' in c['text'] and c['visible']]
        if send_candidates:
            best_candidate = send_candidates[0]
            print(f"\n方式1: 尝试坐标点击 '{best_candidate['text']}'")
            try:
                x = best_candidate['rect']['x'] + best_candidate['rect']['width'] / 2
                y = best_candidate['rect']['y'] + best_candidate['rect']['height'] / 2
                await browser_manager.main_page.mouse.click(x, y)
                await asyncio.sleep(2)
                
                # 检查结果
                result = await browser_manager.main_page.evaluate('''
                    () => {
                        const textarea = document.querySelector('#content-textarea');
                        return textarea ? textarea.textContent.trim() : '';
                    }
                ''')
                if result == '':
                    print("✅ 坐标点击成功！输入框已清空")
                    return
                else:
                    print(f"❌ 坐标点击失败，输入框仍有内容: '{result}'")
            except Exception as e:
                print(f"❌ 坐标点击失败: {str(e)}")
        
        # 方式2: JavaScript直接点击
        print(f"\n方式2: JavaScript直接点击")
        try:
            js_result = await browser_manager.main_page.evaluate('''
                () => {
                    // 查找包含"发送"的元素
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const sendElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        return text.includes('发送') && el.offsetParent !== null;
                    });
                    
                    console.log('找到包含发送的元素数量:', sendElements.length);
                    
                    for (let i = 0; i < sendElements.length; i++) {
                        const el = sendElements[i];
                        console.log(`元素${i+1}:`, el.tagName, el.textContent, el.className);
                        
                        // 尝试点击
                        try {
                            el.click();
                            console.log(`点击元素${i+1}成功`);
                            return {success: true, element: i+1, text: el.textContent};
                        } catch (e) {
                            console.log(`点击元素${i+1}失败:`, e.message);
                        }
                    }
                    
                    return {success: false, count: sendElements.length};
                }
            ''')
            
            print(f"JavaScript点击结果: {js_result}")
            
            if js_result.get('success'):
                await asyncio.sleep(2)
                result = await browser_manager.main_page.evaluate('''
                    () => {
                        const textarea = document.querySelector('#content-textarea');
                        return textarea ? textarea.textContent.trim() : '';
                    }
                ''')
                if result == '':
                    print("✅ JavaScript点击成功！输入框已清空")
                    return
                else:
                    print(f"❌ JavaScript点击失败，输入框仍有内容: '{result}'")
            
        except Exception as e:
            print(f"❌ JavaScript点击失败: {str(e)}")
        
        # 方式3: 尝试Enter键
        print(f"\n方式3: 尝试Enter键")
        try:
            await browser_manager.main_page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            result = await browser_manager.main_page.evaluate('''
                () => {
                    const textarea = document.querySelector('#content-textarea');
                    return textarea ? textarea.textContent.trim() : '';
                }
            ''')
            if result == '':
                print("✅ Enter键成功！输入框已清空")
                return
            else:
                print(f"❌ Enter键失败，输入框仍有内容: '{result}'")
        except Exception as e:
            print(f"❌ Enter键失败: {str(e)}")
        
        # 方式4: 尝试Ctrl+Enter
        print(f"\n方式4: 尝试Ctrl+Enter")
        try:
            await browser_manager.main_page.keyboard.press("Control+Enter")
            await asyncio.sleep(2)
            
            result = await browser_manager.main_page.evaluate('''
                () => {
                    const textarea = document.querySelector('#content-textarea');
                    return textarea ? textarea.textContent.trim() : '';
                }
            ''')
            if result == '':
                print("✅ Ctrl+Enter成功！输入框已清空")
                return
            else:
                print(f"❌ Ctrl+Enter失败，输入框仍有内容: '{result}'")
        except Exception as e:
            print(f"❌ Ctrl+Enter失败: {str(e)}")
        
        print("\n❌ 所有发送方式都失败了")
        
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 不要关闭浏览器，让用户可以手动查看
        print("\n🔍 浏览器保持打开状态，请手动检查页面...")
        input("按Enter键关闭浏览器...")
        try:
            await browser_manager.close()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python debug_precise_send_button.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(precise_send_button_test(url))
