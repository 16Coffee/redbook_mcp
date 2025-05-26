#!/usr/bin/env python3
"""
查找发送按钮的诊断工具
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.infrastructure.browser.browser import BrowserManager

async def find_send_button_diagnosis(url):
    """查找发送按钮"""
    
    print("🔍 查找发送按钮诊断开始...")
    
    browser_manager = BrowserManager()
    
    try:
        await browser_manager.ensure_browser()
        await browser_manager.main_page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        
        # 滚动到底部
        await browser_manager.main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        
        # 激活输入框
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
        
        # 输入一些文本
        await browser_manager.main_page.keyboard.type("测试文本")
        await asyncio.sleep(0.5)
        
        print("\n🔍 查找所有可能的发送按钮...")
        
        # 查找所有可能的发送按钮
        buttons_info = await browser_manager.main_page.evaluate('''
            () => {
                const results = [];
                
                // 1. 查找所有button元素
                const buttons = Array.from(document.querySelectorAll('button'));
                buttons.forEach((btn, index) => {
                    const rect = btn.getBoundingClientRect();
                    results.push({
                        type: 'button',
                        index: index,
                        text: btn.textContent.trim(),
                        visible: btn.offsetParent !== null,
                        enabled: !btn.disabled,
                        className: btn.className,
                        id: btn.id,
                        rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                    });
                });
                
                // 2. 查找包含"发送"文本的元素
                const sendElements = Array.from(document.querySelectorAll('*')).filter(el => 
                    el.textContent && el.textContent.includes('发送')
                );
                sendElements.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    results.push({
                        type: 'send_text',
                        index: index,
                        tag: el.tagName,
                        text: el.textContent.trim(),
                        visible: el.offsetParent !== null,
                        className: el.className,
                        id: el.id,
                        rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                    });
                });
                
                // 3. 查找评论区域附近的可点击元素
                const textarea = document.querySelector('#content-textarea');
                if (textarea) {
                    const textareaRect = textarea.getBoundingClientRect();
                    const nearbyElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.x > textareaRect.x - 100 && 
                               rect.x < textareaRect.x + textareaRect.width + 100 &&
                               rect.y > textareaRect.y - 50 &&
                               rect.y < textareaRect.y + textareaRect.height + 50 &&
                               (el.onclick || el.style.cursor === 'pointer' || el.tagName === 'BUTTON');
                    });
                    
                    nearbyElements.forEach((el, index) => {
                        const rect = el.getBoundingClientRect();
                        results.push({
                            type: 'nearby_clickable',
                            index: index,
                            tag: el.tagName,
                            text: el.textContent.trim(),
                            visible: el.offsetParent !== null,
                            className: el.className,
                            id: el.id,
                            hasOnclick: !!el.onclick,
                            cursor: el.style.cursor,
                            rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                        });
                    });
                }
                
                return results;
            }
        ''')
        
        print(f"\n📊 找到 {len(buttons_info)} 个可能的发送元素:")
        
        for i, btn in enumerate(buttons_info):
            print(f"\n{i+1}. 类型: {btn['type']}")
            print(f"   标签: {btn.get('tag', 'BUTTON')}")
            print(f"   文本: '{btn['text']}'")
            print(f"   可见: {btn['visible']}")
            print(f"   启用: {btn.get('enabled', 'N/A')}")
            print(f"   类名: {btn['className']}")
            print(f"   ID: {btn['id']}")
            print(f"   位置: {btn['rect']}")
            if 'hasOnclick' in btn:
                print(f"   有点击事件: {btn['hasOnclick']}")
                print(f"   鼠标样式: {btn['cursor']}")
        
        # 尝试查找最可能的发送按钮
        print(f"\n🎯 分析最可能的发送按钮...")
        
        likely_send_buttons = []
        for btn in buttons_info:
            score = 0
            reasons = []
            
            # 评分规则
            if '发送' in btn['text']:
                score += 10
                reasons.append("包含'发送'文字")
            
            if btn['visible']:
                score += 5
                reasons.append("可见")
            
            if btn.get('enabled', True):
                score += 3
                reasons.append("启用")
            
            if btn['type'] == 'button':
                score += 2
                reasons.append("是button元素")
            
            if btn['rect']['width'] > 0 and btn['rect']['height'] > 0:
                score += 1
                reasons.append("有尺寸")
            
            if score >= 5:
                likely_send_buttons.append({
                    'button': btn,
                    'score': score,
                    'reasons': reasons
                })
        
        # 按分数排序
        likely_send_buttons.sort(key=lambda x: x['score'], reverse=True)
        
        if likely_send_buttons:
            print(f"找到 {len(likely_send_buttons)} 个可能的发送按钮:")
            for i, item in enumerate(likely_send_buttons[:3]):  # 只显示前3个
                btn = item['button']
                print(f"\n候选 {i+1} (得分: {item['score']}):")
                print(f"   文本: '{btn['text']}'")
                print(f"   类型: {btn['type']}")
                print(f"   原因: {', '.join(item['reasons'])}")
                
            # 尝试点击得分最高的按钮
            best_button = likely_send_buttons[0]['button']
            print(f"\n🎯 尝试点击得分最高的按钮: '{best_button['text']}'")
            
            try:
                if best_button['type'] == 'button':
                    # 通过索引查找button
                    button_element = await browser_manager.main_page.query_selector(f'button:nth-of-type({best_button["index"] + 1})')
                else:
                    # 通过文本查找
                    button_element = await browser_manager.main_page.query_selector(f'text="{best_button["text"]}"')
                
                if button_element:
                    print("找到按钮元素，尝试点击...")
                    await button_element.click()
                    await asyncio.sleep(2)
                    
                    # 检查点击后输入框状态
                    after_click = await browser_manager.main_page.evaluate('''
                        () => {
                            const textarea = document.querySelector('#content-textarea');
                            return textarea ? {
                                textContent: textarea.textContent,
                                value: textarea.value || '',
                                innerText: textarea.innerText
                            } : null;
                        }
                    ''')
                    
                    print(f"点击后输入框状态: {after_click}")
                    
                    if after_click and after_click['textContent'].strip() == '':
                        print("🎉 发送成功！输入框已清空")
                    else:
                        print("❌ 发送可能失败，输入框仍有内容")
                else:
                    print("❌ 无法找到按钮元素")
                    
            except Exception as e:
                print(f"❌ 点击按钮失败: {str(e)}")
        else:
            print("❌ 未找到可能的发送按钮")
        
    except Exception as e:
        print(f"❌ 诊断过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await browser_manager.close()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python debug_send_button.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(find_send_button_diagnosis(url))
