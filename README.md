# Smart RAGFlow

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 基于 RAG (Retrieval-Augmented Generation) 的智能问答系统框架，支持多格式文档解析、向量检索和流式对话。

## 项目简介

Smart RAGFlow 是一个完整的智能问答解决方案，采用前后端分离架构，支持以下核心能力：

- **📄 文档解析**：支持 PDF、Word、Excel、PPT、Markdown 等多种格式
- **🔍 智能检索**：基于 OpenSearch 的向量检索 + MMR 重排序算法
- **💬 流式对话**：兼容 OpenAI 格式的 SSE 流式输出
- **🗂️ 文档管理**：可视化的文档上传、解析和状态管理
- **🔐 用户认证**：JWT 认证，支持多用户会话历史

## 技术架构

### 后端技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 高性能异步 Web 框架 |
| 工作流引擎 | LangGraph | 构建 RAG 处理流程图 |
| 向量数据库 | OpenSearch | 存储和检索文档向量 |
| 关系数据库 | MySQL + SQLAlchemy | 存储文档元数据和用户信息 |
| 缓存 | Redis | 会话缓存和速率限制 |
| 对象存储 | MinIO | 文档文件存储 |
| 嵌入模型 | BGE-M3 / Ollama | 文本向量化 |
| LLM | OpenAI API / DeepSeek | 大语言模型对话生成 |

### 前端技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | 组合式 API，响应式系统 |
| 构建工具 | Vite | 快速开发和构建 |
| UI 组件 | Element Plus (Admin) | 管理后台界面组件 |
| 路由 | Vue Router | 单页应用路由管理 |
| Markdown | Marked + Highlight.js | 消息内容渲染 |

### 系统架构图

```
┌─────────────────┐     ┌─────────────────┐
│   Frontend QA   │     │ Frontend Admin  │
│   (Vue3:3000)   │     │  (Vue3:3001)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │ HTTP
         ┌───────────▼───────────┐
         │     Backend QA        │
         │   (FastAPI:8000)      │
         │  /v1/chat/completions │
         └───────────┬───────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌────────▼────┐ ┌────▼────┐ ┌────▼────┐
│ OpenSearch  │ │  MySQL  │ │  Redis  │
│(向量+全文)  │ │(业务数据)│ │(会话缓存)│
└─────────────┘ └─────────┘ └─────────┘
         │
         │ 轮询任务
┌────────▼────────┐
│  Backend Admin  │
│  (FastAPI:8001) │
│  /api/documents │
└────────┬────────┘
         │
    ┌────┴────┐
┌───▼───┐ ┌──▼────┐
│ MinIO │ │ MySQL │
│(文件) │ │(任务) │
└───────┘ └───────┘
         │
┌────────▼────────┐
│ Backend Parser  │
│   (Worker)      │
│ 解析→分块→向量化 │
└─────────────────┘
```

## 项目结构

```
smart-ragflow/
├── start_all.py              # 一键启动所有服务
├── pyproject.toml            # Python 项目配置
│
├── backend_QA/               # 问答服务 (端口 8000)
│   ├── main.py              # FastAPI 入口
│   ├── api/
│   │   ├── chat.py          # /v1/chat/completions 接口
│   │   ├── auth.py          # JWT 认证
│   │   ├── history.py       # 会话历史管理
│   │   └── download.py      # 文档下载
│   ├── core/
│   │   ├── graph.py         # LangGraph RAG 流程定义
│   │   ├── nodes.py         # 向量化/检索/重排序/生成节点
│   │   └── state.py         # 图状态定义
│   └── services/
│       ├── llm.py           # LLM 客户端
│       ├── opensearch.py    # 向量检索服务
│       ├── mmr.py           # MMR 重排序
│       └── chat_history.py  # 对话历史管理
│
├── backend_admin/            # 文档管理服务 (端口 8001)
│   ├── main.py              # FastAPI 入口
│   ├── api/
│   │   └── documents.py     # 文档 CRUD 接口
│   ├── models/              # SQLAlchemy 模型
│   ├── database/            # 数据库配置
│   └── services/            # 业务逻辑层
│
├── backend_parser/           # 文档解析服务 (Worker)
│   ├── service.py           # DocumentParseService
│   ├── worker.py            # 后台任务轮询
│   ├── deepdoc_parser.py    # 文档解析器
│   ├── chunker.py           # 文本分块
│   ├── embedding.py         # 向量化
│   ├── opensearch_client.py # OpenSearch 客户端
│   └── file_downloader.py   # 文件下载
│
├── backend_common/           # 公共模块
│   ├── clients/             # MinIO / Redis / OpenSearch 客户端
│   ├── config.py            # 全局配置
│   └── models.py            # 共享数据模型
│
├── frontend_QA/              # 问答前端 (端口 3000)
│   ├── src/
│   │   ├── views/
│   │   │   └── ChatView.vue     # 对话界面
│   │   └── utils/
│   │       └── api.js           # API 客户端
│   └── package.json
│
├── frontend_admin/           # 管理后台前端 (端口 3001)
│   ├── src/
│   │   ├── views/
│   │   │   └── DocumentManager.vue  # 文档管理
│   │   └── api/
│   │       └── documents.js     # API 客户端
│   └── package.json
│
└── scripts/                  # 数据库脚本
    ├── create_chat_history_table.sql
    └── migrate_*.sql
```

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- MySQL >= 8.0
- OpenSearch >= 2.0
- Redis >= 6.0
- MinIO (或兼容 S3 的对象存储)
- Ollama (用于本地 Embedding 模型，可选)

### 1. 安装依赖

```bash
# Python 依赖
pip install -e .

# 或如果使用 uv
uv pip install -e .

# 前端依赖
cd frontend_QA && npm install
cd ../frontend_admin && npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、MinIO、OpenAI API 等
```

### 3. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE ragflow CHARACTER SET utf8mb4;"

# 执行初始化脚本
mysql -u root -p ragflow < scripts/create_chat_history_table.sql
```

### 4. 启动服务

#### 方式一：一键启动（推荐）

```bash
# 启动所有服务
python start_all.py

# 或分别启动
python start_all.py --services backend    # 仅启动后端
python start_all.py --services frontend   # 仅启动前端
```

#### 方式二：手动启动

```bash
# 1. 启动文档管理服务
cd backend_admin && uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 2. 启动问答服务
cd backend_QA && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. 启动解析 Worker
cd backend_parser && python worker.py

# 4. 启动前端（新终端）
cd frontend_QA && npm run dev
cd frontend_admin && npm run dev
```

### 5. 访问服务

| 服务 | 地址 |
|------|------|
| 问答前端 | http://localhost:3000 |
| 管理后台 | http://localhost:3001 |
| QA API 文档 | http://localhost:8000/docs |
| Admin API 文档 | http://localhost:8001/docs |

## 核心功能

### RAG 问答流程

```
用户提问
    │
    ▼
┌───────────┐
│ 向量化节点 │ ──→ BGE-M3 Embedding
└─────┬─────┘
      │
      ▼
┌───────────┐
│ 检索节点   │ ──→ OpenSearch KNN 搜索
└─────┬─────┘
      │
      ▼
┌───────────┐
│ 重排序节点 │ ──→ MMR 算法去重
└─────┬─────┘
      │
      ▼
┌───────────┐
│ 生成节点   │ ──→ LLM 流式生成答案
└───────────┘
```

### 文档处理流程

```
上传文档 → 存储 MinIO → 创建任务 → Worker 拉取 → 解析 → 分块 → 向量化 → 索引
```

## API 接口

### QA 服务接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/v1/chat/completions` | 流式问答（OpenAI 兼容） |
| GET | `/v1/history` | 获取会话历史 |
| DELETE | `/v1/history/{session_id}` | 删除会话 |
| POST | `/v1/auth/login` | 用户登录 |
| POST | `/v1/auth/register` | 用户注册 |
| GET | `/health` | 健康检查 |

### Admin 服务接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/documents` | 文档列表（分页） |
| POST | `/api/documents` | 上传文档 |
| DELETE | `/api/documents/{id}` | 删除文档 |
| PUT | `/api/documents/{id}` | 更新文档 |
| POST | `/api/documents/{id}/parse` | 创建解析任务 |
| GET | `/api/documents/{id}/status` | 查询解析状态 |

## 配置说明

### 核心环境变量

```bash
# OpenAI API 配置
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# OpenSearch 配置
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=rag_docs

# 数据库配置
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/ragflow?charset=utf8mb4

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKECT_NAME=smart-ragflow

# Embedding 配置
EMBEDDING_MODEL=bge-m3
EMBEDDING_URL=http://localhost:11434/api/embeddings
```

## 部署建议

### Docker 部署（推荐）

```bash
# [待补充] Docker Compose 配置
```

### 生产环境配置

1. **使用反向代理**：Nginx 统一入口，配置 SSL
2. **数据库优化**：MySQL 配置连接池，定期备份
3. **监控告警**：配置 OpenSearch、Redis、MinIO 监控
4. **日志收集**：统一日志格式，接入 ELK 或 Loki

## 开发指南

### 添加新的文档解析器

1. 在 `backend_parser/` 下实现新的解析器类
2. 继承 `BaseParser` 接口
3. 在 `deepdoc_parser.py` 中注册

### 自定义 RAG 流程

1. 修改 `backend_QA/core/nodes.py` 添加新节点
2. 在 `backend_QA/core/graph.py` 中调整流程图

### 前端开发

```bash
# 问答前端
cd frontend_QA
npm run dev      # 开发模式
npm run build    # 生产构建

# 管理后台
cd frontend_admin
npm run dev      # 开发模式
npm run build    # 生产构建
```

## 测试

```bash
# 运行后端测试
pytest backend_QA/tests backend_admin/tests

# 前端测试
cd frontend_QA && npm run test
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/xxx`
5. 创建 Pull Request

## 常见问题

### Q: 文档解析失败怎么办？

A: 检查以下几点：
- Worker 是否正常启动：`ps aux | grep worker.py`
- MinIO 连接是否正常
- OpenSearch 索引是否存在

### Q: Embedding 服务连接失败？

A: 
- 如果使用 Ollama，确保服务已启动：`ollama list`
- 检查 `EMBEDDING_URL` 配置是否正确

### Q: 前端无法连接后端？

A: 检查 CORS 配置，确保 `CORS_ORIGINS` 包含前端地址。

## 许可证

[MIT License](LICENSE)

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [OpenSearch](https://opensearch.org/)
