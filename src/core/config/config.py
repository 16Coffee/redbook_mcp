"""
配置模块，集中管理所有配置项和常量
"""
import os
import ahocorasick # Added for Aho-Corasick automaton
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BrowserConfig:
    """浏览器配置类"""
    timeout: int = 60000  # 毫秒
    wait_time: int = 5    # 秒
    viewport_width: int = 1280
    viewport_height: int = 800
    headless: bool = False
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

@dataclass
class PathConfig:
    """路径配置类"""
    base_dir: Path
    browser_data_dir: Path
    data_dir: Path
    logs_dir: Path
    
    def __post_init__(self):
        """确保所有目录存在"""
        for path in [self.browser_data_dir, self.data_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)

class Config:
    """统一配置管理类"""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 基础路径配置 - 将browser_data移到项目根目录以提高持久化稳定性
        base_dir = Path(__file__).parent.parent.parent  # 指向项目根目录
        self.paths = PathConfig(
            base_dir=base_dir,
            browser_data_dir=base_dir / "browser_data",  # 移到项目根目录
            data_dir=base_dir / "data",
            logs_dir=base_dir / "data" / "logs"
        )
        
        # 浏览器配置
        self.browser = BrowserConfig(
            timeout=int(os.getenv("BROWSER_TIMEOUT", 60000)),
            wait_time=int(os.getenv("BROWSER_WAIT_TIME", 5)),
            viewport_width=int(os.getenv("VIEWPORT_WIDTH", 1280)),
            viewport_height=int(os.getenv("VIEWPORT_HEIGHT", 800)),
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
        )
        
        # 登录持久化配置
        self.login_persistence = {
            "session_check_interval": 300,  # 5分钟检查一次登录状态
            "max_login_retention_days": 30,  # 登录状态最长保持30天
            "auto_relogin_attempts": 3,     # 自动重新登录尝试次数
            "session_backup_enabled": True,  # 启用会话备份
            "cookie_backup_interval": 1800   # 30分钟备份一次cookie
        }
        
        # 时间戳
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 领域关键词配置
        self.domain_keywords = {
            "美妆": ["口红", "粉底", "眼影", "护肤", "美妆", "化妆", "保湿", "精华", "面膜"],
            "穿搭": ["穿搭", "衣服", "搭配", "时尚", "风格", "单品", "衣橱", "潮流"],
            "美食": ["美食", "好吃", "食谱", "餐厅", "小吃", "甜点", "烘焙", "菜谱"],
            "旅行": ["旅行", "旅游", "景点", "出行", "攻略", "打卡", "度假", "酒店"],
            "母婴": ["宝宝", "母婴", "育儿", "儿童", "婴儿", "辅食", "玩具"],
            "数码": ["数码", "手机", "电脑", "相机", "智能", "设备", "科技"],
            "家居": ["家居", "装修", "家具", "设计", "收纳", "布置", "家装"],
            "健身": ["健身", "运动", "瘦身", "减肥", "训练", "塑形", "肌肉"],
            "AI": ["AI", "人工智能", "大模型", "编程", "开发", "技术", "Claude", "GPT"]
        }
        
        # 评论类型指导
        self.comment_guides = {
            "引流": "生成一条表达认同并引导互动的评论。可以提到自己也在研究相关内容，或表达希望进一步交流的意愿。可以在结尾加上\"有更多问题欢迎私信我\"或\"想了解更多可以找我聊聊\"等邀请语句。",
            "点赞": "生成一条简短的赞美评论，表达对内容的喜爱和支持。可以提到作者名字和笔记的领域，如\"太赞了\！XX的分享总是这么实用\"或\"喜欢这种深度分享\"等。",
            "咨询": "生成一条提问式评论，针对笔记内容询问更多细节或相关信息。可以使用\"请问博主\"或\"想请教一下\"等开头，并提出与笔记内容相关的具体问题。",
            "专业": "生成一条展示专业知识的评论，针对笔记内容提供专业见解或补充信息。可以使用\"作为该领域从业者\"或\"从专业角度来看\"等开头，并在评论中使用与笔记领域相关的专业术语。"
        }
        
        # 重试配置
        self.retry = {
            "max_attempts": int(os.getenv("MAX_RETRY_ATTEMPTS", 3)),
            "base_delay": float(os.getenv("RETRY_BASE_DELAY", 1.0)),
            "backoff_factor": float(os.getenv("RETRY_BACKOFF_FACTOR", 2.0))
        }

        self._build_domain_automaton()

    def _build_domain_automaton(self):
        """Builds the Aho-Corasick automaton for domain detection."""
        A = ahocorasick.Automaton()
        for domain_name, keywords in self.domain_keywords.items():
            for keyword in keywords:
                lkey = keyword.lower()
                # Store a tuple: (original_keyword_case_insensitive, domain_name)
                A.add_word(lkey, (lkey, domain_name))
        A.make_automaton()
        self.domain_automaton = A
        print("Domain detection automaton built.")

    def validate(self):
        """验证配置的有效性"""
        errors = []
        
        if self.browser.timeout <= 0:
            errors.append("浏览器超时时间必须大于0")
        
        if self.browser.wait_time <= 0:
            errors.append("浏览器等待时间必须大于0")
        
        if not self.paths.base_dir.exists():
            errors.append(f"基础目录不存在: {self.paths.base_dir}")
        
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
        
        return True

# 创建全局配置实例
config = Config()

# 向后兼容的变量导出
BASE_DIR = str(config.paths.base_dir)
BROWSER_DATA_DIR = str(config.paths.browser_data_dir)
DATA_DIR = str(config.paths.data_dir)
TIMESTAMP = config.timestamp
DEFAULT_TIMEOUT = config.browser.timeout
DEFAULT_WAIT_TIME = config.browser.wait_time
VIEWPORT_WIDTH = config.browser.viewport_width
VIEWPORT_HEIGHT = config.browser.viewport_height
DOMAIN_KEYWORDS = config.domain_keywords
COMMENT_GUIDES = config.comment_guides
