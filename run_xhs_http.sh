#!/bin/bash

# 小红书MCP服务器 - HTTP协议启动脚本
# 作用: 以HTTP模式启动MCP服务，支持网页端和远程调用

# 配置参数
PORT=8788
HOST="0.0.0.0"  # 使用0.0.0.0允许外部访问，如只需本地访问可改为127.0.0.1
CORS_ORIGINS="*"  # 允许所有源，生产环境应限制为特定域名

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境(如果存在)
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "已激活Python虚拟环境"
fi

# 确保Python模块路径正确
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 显示启动信息
echo "正在启动小红书MCP服务器(HTTP模式)..."
echo "服务地址: http://${HOST}:${PORT}"
echo "允许跨域: ${CORS_ORIGINS}"

# 创建独立的HTTP服务器文件
cat > http_server.py << 'EOF'
"""
小红书MCP HTTP服务器
直接使用FastAPI创建HTTP服务
"""
import sys
import os
import argparse
import asyncio
import inspect
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入原始MCP实例和工具函数
from src.interfaces.mcp.server import mcp, cleanup_resources
from src.interfaces.mcp.server import login_redbook, search_notes, get_note_content, get_note_comments
from src.interfaces.mcp.server import post_comment, post_smart_comment, analyze_note, publish_note_redbook
from src.interfaces.mcp.server import login_douyin, publish_douyin_content
from src.core.logging.logger import logger

# 创建FastAPI应用
app = FastAPI(title="小红书MCP API", version="1.0.0")

# 收集所有工具函数
tool_functions = {
    'login_redbook': login_redbook,
    'search_notes': search_notes,
    'get_note_content': get_note_content, 
    'get_note_comments': get_note_comments,
    'post_comment': post_comment,
    'post_smart_comment': post_smart_comment,
    'analyze_note': analyze_note,
    'publish_note_redbook': publish_note_redbook,
    'login_douyin': login_douyin,
    'publish_douyin_content': publish_douyin_content
}

# 提取工具信息
tools = []
for name, fn in tool_functions.items():
    # 从函数签名中提取参数信息
    sig = inspect.signature(fn)
    parameters = {}
    for param_name, param in sig.parameters.items():
        if param_name != 'self':  # 排除self参数
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else None
            default = None if param.default == inspect.Parameter.empty else param.default
            parameters[param_name] = {
                "type": str(annotation),
                "default": default,
                "required": default == inspect.Parameter.empty
            }
    
    tool_info = {
        "name": name,
        "description": fn.__doc__ or "无描述",
        "parameters": parameters
    }
    tools.append(tool_info)

# 添加CORS中间件
def setup_cors(app, origins):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# MCP接口路由
@app.post("/v1/tools")
async def invoke_tool(request: Request):
    """调用MCP工具"""
    try:
        # 解析请求体
        body = await request.json()
        tool_name = body.get("name")
        parameters = body.get("parameters", {})
        
        # 验证工具是否存在
        if tool_name not in tool_functions:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
        
        # 调用工具函数
        tool_fn = tool_functions[tool_name]
        result = await tool_fn(**parameters)
        
        # 返回结果
        return {"result": result}
    except Exception as e:
        logger.error(f"工具调用失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# 健康检查接口
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "tools_count": len(tools)
    }

# 工具列表接口
@app.get("/v1/tools")
async def list_tools():
    return {"tools": tools}

# 主函数
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小红书MCP HTTP服务器")
    parser.add_argument("--port", type=int, default=8788, help="服务端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务主机")
    parser.add_argument("--cors", type=str, default="*", help="CORS来源")
    
    args = parser.parse_args()
    
    # 配置CORS
    cors_origins = [args.cors] if args.cors != "*" else ["*"]
    setup_cors(app, cors_origins)
    
    # 启动服务
    logger.info(f"HTTP服务器启动中 - http://{args.host}:{args.port}")
    
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    finally:
        # 在主线程退出前执行清理
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(cleanup_resources())
        except:
            pass
EOF

# 运行HTTP服务器
python http_server.py --port $PORT --host "$HOST" --cors "$CORS_ORIGINS"

# 如果启动失败，提供诊断信息
if [ $? -ne 0 ]; then
    echo "启动失败，尝试检查以下问题:"
    echo "1. 端口 ${PORT} 是否已被占用"
    echo "2. 所有依赖是否正确安装(运行 './deploy_all_in_one.sh')"
    echo "3. Python路径是否正确设置"
    
    rm -f http_server.py
    exit 1
fi

# 清理临时文件
rm -f http_server.py 