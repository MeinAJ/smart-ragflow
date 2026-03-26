# Smart RAGFlow

基于 RAG（Retrieval-Augmented Generation，检索增强生成）技术的智能问答系统，支持文档上传、向量化存储、流式问答对话。

## 📑 目录

- [功能特性](#-功能特性)
- [技术架构](#-技术架构)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [详细配置](#-详细配置)
- [API 文档](#-api-文档)
- [RAG 流程详解](#-rag-流程详解)
- [数据模型](#-数据模型)
- [开发指南](#-开发指南)
- [部署说明](#-部署说明)
- [故障排查](#-故障排查)

---

## ✨ 功能特性

### 核心功能

| 功能 | 描述 |
|------|------|
| 🤖 **智能问答** | 基于 RAG 技术的流式问答，支持上下文对话历史 |
| 📄 **文档管理** | 支持 PDF、Word、TXT、Excel、PPT 等多种格式的文档上传和解析 |
| 🔍 **混合检索** | 结合 BM25 文本检索和向量相似度检索，提高检索准确性 |
| 🎯 **MMR 重排序** | 最大边际相关性算法，平衡检索结果的相关性和多样性 |
| 💾 **多存储支持** | OpenSearch 搜索引擎 + Redis 缓存 + MinIO 对象存储 |
| 🔐 **用户认证** | JWT 身份认证，支持用户隔离的会话管理 |
| 💬 **会话管理** | 支持多会话对话、会话重命名、置顶功能 |
| ⚡ **流式响应** | OpenAI 风格的 SSE 流式输出，实时响应 |

### 支持的文档格式

- **PDF** - 支持文本提取和 OCR
- **Word** (.doc, .docx) - Microsoft Word 文档
- **Excel** (.xls, .xlsx) - 表格数据
- **PowerPoint** (.ppt, .pptx) - 演示文稿
- **文本文件** (.txt, .md, .html) - 纯文本和 Markdown

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层                                    │
├──────────────────────────┬──────────────────────────────────────┤
│   frontend_QA (Vue 3)    │   frontend_admin (Vue 3)             │
│   端口: 3000              │   端口: 3001                          │
│   用户问答界面            │   文档管理后台                        │
└──────────┬───────────────┴──────────────┬───────────────────────┘
           │                              │
           └──────────────┬───────────────┘
                          │ HTTP / WebSocket
┌─────────────────────────┴───────────────────────────────────────┐
│                      API 网关层 (FastAPI)                        │
├──────────────────────────┬──────────────────────────────────────┤
│   backend_QA (端口 8000)  │   backend_admin (端口 8001)          │
│   - 问答 API              │   - 文档管理 API                     │
│   - 认证 API              │   - 文件上传/下载                    │
│   - 历史记录 API          │                                      │
└──────────┬───────────────┴──────────────┬───────────────────────┘
           │                              │
┌──────────┴──────────────────────────────┴───────────────────────┐
│                      服务层                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ RAG Graph   │  │ Embedding   │  │ LLM Service │  │ MMR    │ │
│  │ LangGraph   │  │ BGE-M3      │  │ DeepSeek    │  │ Rerank │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────┘ │
└──────────┬─────────────────────────────┬────────────────────────┘
           │                             │
┌──────────┴──────────┐  ┌──────────────┴──────────┐
│    数据存储层        │  │      基础设施层          │
├─────────────────────┤  ├─────────────────────────┤
│  MySQL              │  │  Redis (缓存/会话)       │
│  - users            │  │                         │
│  - user_session     │  │  MinIO (对象存储)        │
│  - chat_history     │  │                         │
│  - documents        │  │  OpenSearch (向量检索)   │
└─────────────────────┘  └─────────────────────────┘
```

### 后端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| Web 框架 | FastAPI | ^0.104 | 高性能异步 Web 框架，自动生成 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn | ^0.24 | 异步 ASGI 服务器，支持 HTTP/1.1 和 WebSocket |
| 工作流引擎 | LangGraph | ^0.0.40 | LLM 应用状态图编排，定义 RAG 流程 |
| LLM 框架 | LangChain | ^0.1.0 | 大语言模型应用开发框架 |
| 向量检索 | OpenSearch | 2.x | 分布式搜索和分析引擎，支持 k-NN 向量检索 |
| 缓存 | Redis | 6.x+ | 内存数据结构存储，用于会话历史和上下文缓存 |
| 对象存储 | MinIO | 最新 | 高性能对象存储，兼容 S3 API |
| 向量嵌入 | BGE-M3 | - | 文本向量化模型，输出 1024 维向量 |
| 数据库 | MySQL | 8.0+ | 用户、会话、聊天记录持久化 |
| ORM | SQLAlchemy | ^2.0.0 | 数据库对象关系映射 |
| 认证 | python-jose + bcrypt | - | JWT Token 生成和密码哈希 |
| 文档解析 | pdfplumber + python-docx | - | 多格式文档解析 |

### 前端技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 (Composition API) | 渐进式 JavaScript 框架 |
| 构建工具 | Vite | 下一代前端构建工具 |
| UI 组件 | 自定义组件 | DeepSeek 风格的深色主题设计 |
| HTTP 客户端 | Fetch API | 原生 fetch，支持 SSE 流式 |
| 路由 | Vue Router | 单页应用路由管理 |

---

## 📁 项目结构

```
smart-ragflow/
├── 📁 backend_QA/                 # 问答服务 (端口 8000)
│   ├── 📁 api/                    # API 路由层
│   │   ├── __init__.py
│   │   ├── auth.py               # JWT 认证接口 (/auth/*)
│   │   ├── chat.py               # 问答流式接口 (/v1/chat/completions)
│   │   ├── history.py            # 会话历史接口 (/history/*)
│   │   └── download.py           # 文件下载接口 (/files/*)
│   ├── 📁 core/                   # RAG 核心逻辑
│   │   ├── __init__.py
│   │   ├── graph.py              # LangGraph RAG 流程图定义
│   │   ├── nodes.py              # RAG 节点实现 (向量化/检索/重排序/生成)
│   │   └── state.py              # GraphState 状态定义
│   ├── 📁 services/               # 业务服务层
│   │   ├── __init__.py
│   │   ├── chat_history.py       # 聊天记录服务 (MySQL + Redis)
│   │   ├── embedding.py          # 嵌入模型客户端
│   │   ├── llm.py                # LLM 客户端 (DeepSeek/OpenAI)
│   │   ├── mmr.py                # MMR 重排序算法
│   │   └── opensearch.py         # OpenSearch 混合检索
│   ├── 📁 utils/                  # 工具函数
│   │   └── sse.py                # SSE 流式响应辅助
│   ├── __init__.py
│   └── main.py                   # FastAPI 应用入口
│
├── 📁 backend_admin/              # 文档管理服务 (端口 8001)
│   ├── 📁 api/
│   │   └── documents.py          # 文档 CRUD 接口
│   ├── 📁 services/
│   │   └── document_service.py   # 文档业务逻辑
│   ├── 📁 models/
│   └── main.py
│
├── 📁 backend_parser/             # 文档解析服务
│   ├── worker.py                 # 解析工作进程 (消费者)
│   ├── service.py                # 解析服务逻辑
│   ├── chunker.py                # 文本分块 (按 Token)
│   ├── deepdoc_parser.py         # 文档解析器 (PDF/Word 等)
│   ├── embedding.py              # 向量嵌入客户端
│   ├── document_models.py        # 文档数据模型
│   └── cli.py                    # 命令行工具
│
├── 📁 backend_common/             # 共享基础设施
│   ├── __init__.py               # 统一导出
│   ├── config.py                 # 配置管理 (pydantic-settings)
│   ├── database.py               # MySQL 数据库连接
│   ├── models.py                 # SQLAlchemy 数据模型
│   └── 📁 clients/                # 各种客户端封装
│       ├── embedding_client.py   # 嵌入服务客户端
│       ├── minio_client.py       # MinIO 客户端
│       ├── opensearch_client.py  # OpenSearch 客户端
│       └── redis_client.py       # Redis 客户端
│
├── 📁 frontend_QA/                # 用户问答前端 (端口 3000)
│   ├── 📁 src/
│   │   ├── 📁 views/
│   │   │   ├── ChatView.vue      # 聊天主界面
│   │   │   └── AuthView.vue      # 登录/注册页面
│   │   ├── 📁 components/
│   │   │   ├── ChatMessage.vue   # 消息气泡组件
│   │   │   └── SessionItem.vue   # 会话项组件
│   │   ├── 📁 utils/
│   │   │   ├── api.js            # API 调用封装
│   │   │   └── auth.js           # 认证工具函数
│   │   ├── 📁 router/
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js            # Vite 配置 (含代理)
│
├── 📁 frontend_admin/             # 文档管理前端 (端口 3001)
│   └── 📁 src/
│       └── 📁 views/
│           └── DocumentManager.vue
│
├── start_all.py                   # 一键启动脚本
├── pyproject.toml                 # Python 项目配置 (依赖/脚本)
├── uv.lock                        # uv 依赖锁定文件
├── .env.example                   # 环境变量模板
└── README.md                      # 项目说明
```

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 推荐使用 3.12 |
| Node.js | 18+ | 前端构建需要 |
| MySQL | 8.0+ | 数据持久化 |
| Redis | 6.0+ | 缓存和会话 |
| OpenSearch | 2.x | 向量检索 |
| MinIO | 最新 | 对象存储 |

### 1. 克隆项目

```bash
git clone <repository-url>
cd smart-ragflow
```

### 2. 安装 Python 依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 3. 安装前端依赖

```bash
# 用户端
cd frontend_QA
npm install

# 管理端
cd ../frontend_admin
npm install
cd ..
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写实际配置
```

**必需配置项：**

```env
# LLM API (支持 OpenAI/DeepSeek 等)
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 数据库
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ragflow?charset=utf8mb4

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=rag_docs

# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=smart-ragflow

# 嵌入模型 (Ollama 或自定义服务)
EMBEDDING_URL=http://localhost:11434/api/embeddings
EMBEDDING_MODEL=bge-m3
```

### 5. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE ragflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 启动服务时会自动创建表
```

### 6. 启动服务

#### 方式一：一键启动（推荐开发环境）

```bash
python start_all.py
```

#### 方式二：分别启动（便于调试）

```bash
# Terminal 1: 问答服务
python start_all.py --services client

# Terminal 2: 文档管理服务
python start_all.py --services admin

# Terminal 3: 解析服务
python start_all.py --services parser

# Terminal 4: 用户前端
cd frontend_QA && npm run dev

# Terminal 5: 管理前端
cd frontend_admin && npm run dev
```

### 7. 访问服务

| 服务 | URL | 说明 |
|------|-----|------|
| 用户端 | http://localhost:3000 | 问答界面 |
| 管理端 | http://localhost:3001 | 文档管理 |
| QA API | http://localhost:8000/docs | 问答 API 文档 |
| Admin API | http://localhost:8001/docs | 管理 API 文档 |

---

## ⚙️ 详细配置

### 完整环境变量说明

#### LLM 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | - | LLM API 密钥 |
| `OPENAI_BASE_URL` | https://api.openai.com/v1 | API 基础 URL |
| `OPENAI_MODEL` | gpt-3.5-turbo | 默认模型名称 |

#### 数据库配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | - | MySQL 连接 URL |

#### OpenSearch 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENSEARCH_HOST` | localhost | 主机地址 |
| `OPENSEARCH_PORT` | 9200 | 服务端口 |
| `OPENSEARCH_INDEX` | rag_docs | 索引名称 |

#### Redis 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REDIS_URL` | redis://localhost:6379 | 连接 URL |
| `REDIS_DB` | 0 | 数据库编号 |

#### MinIO 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MINIO_ENDPOINT` | localhost:9000 | 服务端点 |
| `MINIO_PUBLIC_ENDPOINT` | http://localhost:9000 | 公网访问端点 |
| `MINIO_ACCESS_KEY` | minioadmin | 访问密钥 |
| `MINIO_SECRET_KEY` | minioadmin | 秘密密钥 |
| `MINIO_BUCKET_NAME` | smart-ragflow | Bucket 名称 |
| `MINIO_SECURE` | false | 是否使用 HTTPS |

#### 嵌入模型配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `EMBEDDING_URL` | - | 嵌入服务地址 |
| `EMBEDDING_MODEL` | bge-m3 | 模型名称 |
| `EMBEDDING_TIMEOUT` | 180 | 请求超时(秒) |

#### MMR 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MMR_LAMBDA` | 0.5 | 多样性权重 (0-1) |
| `MMR_TOP_K` | 5 | 返回文档数量 |

#### Tokenizer 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TOKENIZER_TYPE` | tiktoken | Tokenizer 类型 |
| `TIKTOKEN_ENCODING` | cl100k_base | Encoding 名称 |

---

## 📖 API 文档

启动服务后访问自动生成的文档：
- QA API: http://localhost:8000/docs
- Admin API: http://localhost:8001/docs

### 认证接口

#### POST /auth/register
用户注册

**请求体：**
```json
{
  "username": "testuser",
  "password": "password123",
  "email": "test@example.com",
  "nickname": "测试用户"
}
```

**响应：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "nickname": "测试用户",
    "is_admin": false
  }
}
```

#### POST /auth/login
用户登录

**请求体：**
```json
{
  "username": "testuser",
  "password": "password123"
}
```

#### GET /auth/me
获取当前用户信息

**请求头：**
```
Authorization: Bearer <token>
```

### 问答接口

#### POST /v1/chat/completions
智能问答（支持 SSE 流式输出）

**请求体：**
```json
{
  "messages": [
    {"role": "user", "content": "介绍一下 Spring Boot"}
  ],
  "stream": true,
  "model": "deepseek-chat",
  "session_id": "sess_xxx"
}
```

**响应（SSE 流式）：**
```
event: context_docs
data: {"docs": [{"title": "Spring Boot 文档", "score": 0.95}]}

data: {"choices": [{"delta": {"content": "Spring"}}]}
data: {"choices": [{"delta": {"content": " Boot"}}]}
data: [DONE]
```

### 会话历史接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history/sessions` | 获取会话列表 |
| GET | `/history/sessions/{id}` | 获取会话详情 |
| GET | `/history/sessions/{id}/messages` | 获取会话消息 |
| PUT | `/history/sessions/{id}/name` | 修改会话名称 |
| PUT | `/history/sessions/{id}/pin` | 置顶/取消置顶 |
| DELETE | `/history/sessions/{id}` | 删除会话 |

### 文档管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/documents` | 上传文档 |
| GET | `/api/documents` | 获取文档列表 |
| GET | `/api/documents/{id}` | 获取文档详情 |
| DELETE | `/api/documents/{id}` | 删除文档 |
| GET | `/files/{id}` | 下载文档 |

---

## 🔧 RAG 流程详解

### 流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG 处理流程                                   │
└─────────────────────────────────────────────────────────────────────┘

  用户提问
     │
     ▼
┌─────────────────┐
│  1. 问题向量化   │  BGE-M3 模型将问题转换为 1024 维向量
│   (Vectorize)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 混合检索     │  OpenSearch 执行 BM25 + KNN 向量检索
│   (Retrieve)    │  返回 Top 10 候选文档
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. MMR 重排序   │  最大边际相关性算法
│   (Rerank)      │  平衡相关性和多样性，返回 Top 5
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 上下文组装   │  组装检索结果到 Prompt
│  (Build Prompt) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. LLM 生成     │  调用 DeepSeek/OpenAI 流式生成答案
│   (Generate)    │
└────────┬────────┘
         │
         ▼
  SSE 流式输出给用户
```

### 核心代码实现

#### LangGraph 状态定义 (`backend_QA/core/state.py`)

```python
class GraphState(TypedDict):
    question: str              # 原始问题
    question_vector: List[float]   # 向量化结果 (1024维)
    retrieved_docs: List[dict]     # 检索到的文档
    reranked_docs: List[dict]      # MMR 重排序后的文档
    answer: Optional[str]          # 生成的答案
    error: Optional[str]           # 错误信息
```

#### 节点函数 (`backend_QA/core/nodes.py`)

- **vectorize_node**: 调用 BGE-M3 服务进行向量化
- **retrieve_node**: 执行 OpenSearch 混合检索
- **rerank_node**: 执行 MMR 重排序
- **generate_node**: 调用 LLM 生成答案

---

## 🗄️ 数据模型

### 用户模型 (User)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| username | VARCHAR(50) | 用户名，唯一 |
| email | VARCHAR(100) | 邮箱，唯一 |
| password_hash | VARCHAR(255) | bcrypt 密码哈希 |
| nickname | VARCHAR(50) | 昵称 |
| avatar | VARCHAR(500) | 头像 URL |
| is_active | BOOLEAN | 是否激活 |
| is_admin | BOOLEAN | 是否管理员 |
| last_login_at | DATETIME | 最后登录时间 |
| created_at | DATETIME | 创建时间 |

### 会话模型 (UserSession)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| user_id | BIGINT | 用户 ID |
| session_id | VARCHAR(64) | 会话唯一标识 |
| session_name | VARCHAR(200) | 会话名称（可修改） |
| message_count | INT | 消息数量 |
| last_message_at | DATETIME | 最后消息时间 |
| is_pinned | SMALLINT | 是否置顶 |
| created_at | DATETIME | 创建时间 |

### 聊天记录 (ChatHistory)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| user_id | BIGINT | 用户 ID |
| session_id | VARCHAR(64) | 会话 ID |
| role | VARCHAR(20) | 角色 (user/assistant) |
| content | TEXT | 消息内容 |
| model | VARCHAR(50) | 使用的模型 |
| tokens_used | INT | Token 消耗 |
| created_at | DATETIME | 创建时间 |

### 文档模型 (Document)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) | 主键 |
| file_name | VARCHAR(255) | 文件名 |
| file_size | BIGINT | 文件大小 |
| file_md5 | VARCHAR(32) | MD5 校验 |
| file_ext | VARCHAR(20) | 文件扩展名 |
| file_url | VARCHAR(500) | MinIO URL |
| parse_status | SMALLINT | 解析状态 |
| chunk_count | INT | 分块数量 |
| created_at | DATETIME | 创建时间 |

---

## 🛠️ 开发指南

### 代码规范

1. **导入规范**
   - 使用绝对导入: `from backend_common import ...`
   - 避免相对导入: `from .. import ...`

2. **文档字符串**
   - 所有函数、类必须添加 docstring
   - 使用 Google 风格

```python
def example_function(param1: str, param2: int) -> dict:
    """
    函数简要说明。
    
    详细说明函数的功能、使用场景等。
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ValueError: 异常说明
    """
    pass
```

3. **异步编程**
   - HTTP 客户端、数据库操作优先使用异步
   - 使用 `async/await` 语法

4. **错误处理**
   - 捕获异常并记录日志
   - 不要静默处理错误

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = await some_async_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
    raise HTTPException(status_code=500, detail="操作失败")
```

5. **日志记录**
   - 使用 logging 模块
   - 关键步骤记录 INFO 级别
   - 错误记录 ERROR 级别

### 添加新 API

```python
# backend_QA/api/example.py
from fastapi import APIRouter, Depends
from backend_QA.api.auth import get_current_user_id

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/")
async def example(
    current_user_id: int = Depends(get_current_user_id)
):
    """
    示例接口。
    
    Returns:
        dict: 返回数据
    """
    return {"message": "Hello", "user_id": current_user_id}

# 在 main.py 中注册
from backend_QA.api import example
app.include_router(example.router)
```

### 数据库迁移

```python
from backend_common import Base, DatabaseClient
from backend_common.models import UserSession

db = DatabaseClient()

# 创建指定表
Base.metadata.create_all(bind=db.engine, tables=[UserSession.__table__])
```

---

## 📦 部署说明

### Docker 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: ragflow
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      discovery.type: single-node
      plugins.security.disabled: true
    ports:
      - "9200:9200"
    volumes:
      - opensearch_data:/usr/share/opensearch/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend_qa:
    build: .
    command: uvicorn backend_QA.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - mysql
      - redis
      - opensearch
      - minio

  backend_admin:
    build: .
    command: uvicorn backend_admin.main:app --host 0.0.0.0 --port 8001
    ports:
      - "8001:8001"
    env_file:
      - .env
    depends_on:
      - mysql
      - minio

  frontend_qa:
    build: ./frontend_QA
    ports:
      - "3000:3000"
    depends_on:
      - backend_qa

volumes:
  mysql_data:
  opensearch_data:
  minio_data:
```

### 生产环境配置

1. **关闭调试模式**
   ```env
   DEBUG=false
   ```

2. **修改 JWT Secret**
   编辑 `backend_QA/api/auth.py`：
   ```python
   SECRET_KEY = "your-strong-secret-key-here"  # 生产环境请更换
   ```

3. **配置 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

4. **数据库连接池**
   ```python
   # database.py 中配置
   engine = create_engine(
       DATABASE_URL,
       pool_size=10,
       max_overflow=20,
       pool_pre_ping=True
   )
   ```

5. **日志级别**
   ```python
   logging.basicConfig(
       level=logging.WARNING,  # 生产环境使用 WARNING
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   )
   ```

---

## 🔍 故障排查

### 常见问题

#### 1. 导入错误 `ImportError: cannot import name 'xxx'`

**解决：** 确保 PYTHONPATH 设置正确
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

#### 2. 数据库连接失败

**检查：**
- MySQL 服务是否运行
- 数据库是否存在
- 用户名密码是否正确

#### 3. OpenSearch 连接失败

**检查：**
- OpenSearch 服务是否运行
- `plugins.security.disabled` 是否设置为 true（开发环境）

#### 4. 嵌入服务超时

**解决：**
- 增加 `EMBEDDING_TIMEOUT`
- 检查嵌入服务是否可用

#### 5. 前端代理失败

**检查：**
- Vite 配置中的代理目标是否正确
- 后端服务是否运行在指定端口

### 调试技巧

1. **查看日志**
   ```bash
   tail -f /tmp/backend.log
   ```

2. **API 测试**
   ```bash
   curl http://localhost:8000/health
   ```

3. **数据库查询**
   ```bash
   mysql -u root -p ragflow -e "SHOW TABLES;"
   ```

---

## 📄 许可证

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 GitHub Issue 联系。

---

**Smart RAGFlow** © 2024 - 智能问答系统
