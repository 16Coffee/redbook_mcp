"""
小红书MCP服务器主入口
重构后的架构入口点
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入并运行MCP服务器
if __name__ == "__main__":
    from src.interfaces.mcp.server import main
    main()
