"""
工具函数模块，提供各种辅助功能
"""
import re
import json
from typing import List, Dict, Any
# Updated import to get the full config object
from src.core.config.config import config

def extract_text(text, prefix, suffix=None):
    """从文本中提取特定前缀和后缀之间的内容
    
    Args:
        text (str): 要处理的文本
        prefix (str): 内容前缀
        suffix (str, optional): 内容后缀. 默认为None.
    
    Returns:
        str: 提取的内容，如果未找到则返回空字符串
    """
    if prefix not in text:
        return ""
    
    start = text.find(prefix) + len(prefix)
    
    if suffix:
        end = text.find(suffix, start)
        if end == -1:
            return text[start:].strip()
        return text[start:end].strip()
    else:
        return text[start:].strip()

def parse_note_content(content_text):
    """解析笔记内容文本，提取标题、作者、发布时间和内容
    
    Args:
        content_text (str): 笔记内容文本
    
    Returns:
        dict: 解析后的笔记内容
    """
    content_lines = content_text.strip().split('\n')
    post_content = {}
    
    # 提取标题、作者、发布时间和内容
    for i, line in enumerate(content_lines):
        if line.startswith("标题:"):
            post_content["标题"] = line.replace("标题:", "").strip()
        elif line.startswith("作者:"):
            post_content["作者"] = line.replace("作者:", "").strip()
        elif line.startswith("发布时间:"):
            post_content["发布时间"] = line.replace("发布时间:", "").strip()
        elif line.startswith("内容:"):
            # 内容可能有多行，获取剩余所有行
            content_text = "\n".join(content_lines[i+1:]).strip()
            post_content["内容"] = content_text
            break
    
    # 如果没有提取到标题或内容，设置默认值
    if "标题" not in post_content or not post_content["标题"]:
        post_content["标题"] = "未知标题"
    if "作者" not in post_content or not post_content["作者"]:
        post_content["作者"] = "未知作者"
    if "内容" not in post_content or not post_content["内容"]:
        post_content["内容"] = "未能获取内容"
    
    return post_content

def detect_domain(title, content):
    """检测笔记所属领域
    
    Args:
        title (str): 笔记标题
        content (str): 笔记内容
    
    Returns:
        list: 检测到的领域列表
    """
    found_domains = set()
    combined_text = f"{title} {content}".lower()

    # Use the Aho-Corasick automaton from the config
    # The automaton stores (keyword_found, domain_name) tuples
    for end_index, (keyword_found, domain_name) in config.domain_automaton.iter(combined_text):
        found_domains.add(domain_name)
    
    # 如果没有检测到明确的领域，默认为生活方式
    if not found_domains:
        return ["生活"]
    
    return list(found_domains)

def extract_keywords(text, limit=20):
    """从文本中提取关键词
    
    Args:
        text (str): 要处理的文本
        limit (int, optional): 返回的关键词数量限制. 默认为20.
    
    Returns:
        list: 提取的关键词列表
    """
    # 简单分词，提取中文词和英文单词
    words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}', text)
    
    # 去重，取前limit个
    unique_words = list(set(words))
    return unique_words[:limit]

def format_json_response(data):
    """格式化JSON响应数据
    
    Args:
        data (dict): 要格式化的数据
    
    Returns:
        str: 格式化的JSON字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)

def safe_get(data, key, default=""):
    """安全地从字典中获取值
    
    Args:
        data (dict): 源数据字典
        key (str): 要获取的键
        default (any, optional): 默认值. 默认为空字符串.
    
    Returns:
        any: 获取的值或默认值
    """
    return data.get(key, default)
