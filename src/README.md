# 🏗️ 项目架构说明

## 📁 目录结构

```
src/
├── core/                    # 核心基础设施层
│   ├── base/               # 基础工具类
│   │   ├── base_manager.py # 基础管理器
│   │   ├── decorators.py   # 装饰器
│   │   └── utils.py        # 工具函数
│   ├── config/             # 配置管理
│   │   └── config.py       # 配置文件
│   ├── logging/            # 日志系统
│   │   └── logger.py       # 日志管理
│   └── exceptions/         # 异常定义
│       └── exceptions.py   # 自定义异常
├── domain/                 # 领域层
│   ├── models/             # 领域模型
│   ├── services/           # 领域服务
│   │   ├── notes.py        # 笔记服务
│   │   ├── comments.py     # 评论服务
│   │   ├── publish.py      # 发布服务
│   │   ├── comment_handler.py      # 评论处理器
│   │   └── image_mode_handler.py   # 图片模式处理器
│   └── repositories/       # 仓储接口
├── infrastructure/         # 基础设施层
│   ├── browser/            # 浏览器相关
│   │   ├── browser.py      # 浏览器管理
│   │   └── waiter.py       # 等待器
│   ├── cache/              # 缓存实现
│   │   └── cache.py        # 缓存管理
│   └── storage/            # 存储实现
├── application/            # 应用层
│   ├── use_cases/          # 用例实现
│   └── dto/                # 数据传输对象
└── interfaces/             # 接口层
    ├── mcp/                # MCP接口
    │   ├── server.py       # MCP服务器
    │   └── mcp_tools.py    # MCP工具
    └── cli/                # 命令行接口
```

## 🎯 架构原则

### 1. 分层架构 (Layered Architecture)
- **接口层 (Interfaces)**: 处理外部请求和响应
- **应用层 (Application)**: 编排业务流程
- **领域层 (Domain)**: 核心业务逻辑
- **基础设施层 (Infrastructure)**: 技术实现细节
- **核心层 (Core)**: 公共基础设施

### 2. 依赖倒置原则
- 高层模块不依赖低层模块
- 抽象不依赖具体实现
- 具体实现依赖抽象

### 3. 单一职责原则
- 每个模块只有一个变化的理由
- 高内聚、低耦合

## 📋 迁移映射

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `modules/config.py` | `src/core/config/config.py` | 配置管理 |
| `modules/logger.py` | `src/core/logging/logger.py` | 日志系统 |
| `modules/exceptions.py` | `src/core/exceptions/exceptions.py` | 异常定义 |
| `modules/base_manager.py` | `src/core/base/base_manager.py` | 基础管理器 |
| `modules/decorators.py` | `src/core/base/decorators.py` | 装饰器 |
| `modules/utils.py` | `src/core/base/utils.py` | 工具函数 |
| `modules/browser.py` | `src/infrastructure/browser/browser.py` | 浏览器管理 |
| `modules/waiter.py` | `src/infrastructure/browser/waiter.py` | 等待器 |
| `modules/cache.py` | `src/infrastructure/cache/cache.py` | 缓存管理 |
| `modules/notes.py` | `src/domain/services/notes.py` | 笔记服务 |
| `modules/comments.py` | `src/domain/services/comments.py` | 评论服务 |
| `modules/publish.py` | `src/domain/services/publish.py` | 发布服务 |
| `modules/comment_handler.py` | `src/domain/services/comment_handler.py` | 评论处理器 |
| `modules/image_mode_handler.py` | `src/domain/services/image_mode_handler.py` | 图片处理器 |
| `modules/mcp_tools.py` | `src/interfaces/mcp/mcp_tools.py` | MCP工具 |
| `main.py` | `src/interfaces/mcp/server.py` | MCP服务器 |

## 🚀 使用方式

### 启动MCP服务器
```bash
python -m src.interfaces.mcp.server
```

### 开发模式
```bash
python -m src.interfaces.mcp.server --dev
```

## 🔧 扩展指南

### 添加新的领域服务
1. 在 `src/domain/services/` 创建服务文件
2. 在 `src/domain/models/` 定义相关模型
3. 在 `src/application/use_cases/` 创建用例
4. 在接口层暴露功能

### 添加新的基础设施
1. 在 `src/infrastructure/` 对应目录添加实现
2. 定义抽象接口
3. 在依赖注入中注册

### 添加新的接口
1. 在 `src/interfaces/` 创建新的接口目录
2. 实现接口适配器
3. 配置路由和中间件 