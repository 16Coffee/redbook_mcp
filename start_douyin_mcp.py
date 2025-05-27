#!/usr/bin/env python3
"""
抖音 MCP 服务器启动脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    from src.interfaces.mcp.douyin_server import main
    main()
