"""
自定义异常类模块，提供统一的异常处理机制
"""

class RedBookMCPException(Exception):
    """小红书MCP工具基础异常类"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class BrowserException(RedBookMCPException):
    """浏览器相关异常"""
    pass

class LoginException(RedBookMCPException):
    """登录相关异常"""
    pass

class ContentException(RedBookMCPException):
    """内容获取相关异常"""
    pass

class PublishException(RedBookMCPException):
    """发布相关异常"""
    pass

class NetworkException(RedBookMCPException):
    """网络相关异常"""
    pass 