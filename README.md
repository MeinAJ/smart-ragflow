# Smart RAGFlow

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange)
![OpenSearch](https://img.shields.io/badge/OpenSearch-2.x-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 基于 RAG (Retrieval-Augmented Generation) 的智能问答系统框架，采用 LangGraph 工作流引擎，支持多格式文档解析、混合检索（BM25+向量）和流式对话。

## 项目简介

Smart RAGFlow 是一个完整的智能问答解决方案，采用前后端分离的微服务架构，为企业知识库问答场景提供开箱即用的解决方案。

### 核心能力

| 能力 | 说明 | 技术实现 |
|------|------|----------|
| 📄 **多格式文档解析** | 支持 PDF、Word、Excel、PPT、Markdown、TXT 等格式 | pdfplumber、python-docx、openpyxl |
| 🔍 **混合检索** | BM25 全文检索 + KNN 向量检索 | OpenSearch hybrid search |
| 🎯 **智能重排序** | MMR (Maximal Marginal Relevance) 算法去重 | 自定义 MMR 实现 |
| 💬 **流式对话** | 兼容 OpenAI API 格式的 SSE 流式输出 | FastAPI StreamingResponse |
| 🗂️ **会话管理** | 支持多用户、多会话历史记录 | MySQL + Redis 双存储 |
| 🔐 **用户认证** | JWT Token 认证，支持用户注册/登录 | python-jose + bcrypt |

### 业务场景

- **企业知识库问答**：基于内部文档的智能客服、知识检索
- **智能文档助手**：个人文档管理、内容问答、信息提取
- **教育培训助手**：教材问答、学习辅导、内容总结
- **法律/医疗咨询**：基于专业文档的问答系统

## 技术架构

### 系统架构图

```mermaid
graph TB
    subgraph Frontend["前端层"]
        F1[Frontend QA<br/>Vue3 + Vite<br/>端口:3000]
        F2[Frontend Admin<br/>Vue3 + Element Plus<br/>端口:3001]
    end

    subgraph API["API 网关层"]
        A1[Backend QA<br/>FastAPI<br/>端口:8000]
        A2[Backend Admin<br/>FastAPI<br/>端口:8001]
    end

    subgraph Core["核心处理层"]
        C1[LangGraph<br/>RAG 工作流]
        C2[Parser Worker<br/>文档解析服务]
    end

    subgraph Storage["存储层"]
        S1[(OpenSearch<br/>向量+全文检索)]
        S2[(MySQL<br/>业务数据)]
        S3[(Redis<br/>会话缓存)]
        S4[(MinIO<br/>文件存储)]
    end

    subgraph External["外部服务"]
        E1[Embedding 服务<br/>BGE-M3/Ollama]
        E2[LLM 服务<br/>OpenAI/DeepSeek]
    end

    F1 -->|HTTP| A1
    F2 -->|HTTP| A2
    A1 -->|调用| C1
    A2 -->|创建任务| C2
    C1 -->|检索| S1
    C1 -->|获取历史| S3
    C2 -->|读取/写入| S4
    C2 -->|索引| S1
    A1 -->|获取上下文| S2
    A2 -->|CRUD| S2
    C1 -->|向量化| E1
    C1 -->|生成答案| E2
    C2 -->|下载文件| S4
```

### RAG 流程时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as Frontend QA
    participant QA as Backend QA
    participant G as LangGraph
    participant E as Embedding 服务
    participant OS as OpenSearch
    participant LLM as LLM 服务
    participant R as Redis

    U->>F: 输入问题
    F->>QA: POST /v1/chat/completions<br/>messages + session_id
    
    QA->>R: 获取历史对话上下文
    R-->>QA: 返回历史消息
    
    QA->>G: 执行 RAG 流程
    
    rect rgb(230, 245, 255)
        Note over G,E: 向量化节点
        G->>E: embed(question)
        E-->>G: 返回 question_vector
    end
    
    rect rgb(255, 245, 230)
        Note over G,OS: 检索节点
        G->>OS: hybrid_search(query, vector)
        OS-->>G: 返回 retrieved_docs
    end
    
    rect rgb(230, 255, 230)
        Note over G: 重排序节点
        G->>G: mmr_rerank(docs, vector)
        G-->>G: 返回 reranked_docs
    end
    
    rect rgb(255, 230, 245)
        Note over G,LLM: 生成节点
        G->>LLM: generate_stream(question, context, history)
        loop 流式生成
            LLM-->>G: token
            G-->>QA: token
            QA-->>F: SSE data
            F-->>U: 显示答案
        end
    end
    
    QA->>R: 保存对话历史
```

### 文档处理流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as Frontend Admin
    participant A as Backend Admin
    participant DB as MySQL
    participant W as Parser Worker
    participant M as MinIO
    participant P as Parser
    participant E as Embedding
    participant OS as OpenSearch

    U->>F: 上传文档
    F->>A: POST /api/documents
    A->>M: 上传文件
    M-->>A: 返回 file_url
    A->>DB: 创建文档记录
    A->>DB: 创建解析任务
    A-->>F: 返回 doc_id
    
    loop 轮询任务
        W->>DB: 查询待解析任务
        DB-->>W: 返回任务
    end
    
    W->>M: 下载文件
    M-->>W: 返回文件内容
    W->>P: 解析文档
    P-->>W: 返回文本块
    W->>E: 向量化 chunks
    E-->>W: 返回 vectors
    W->>OS: 索引文档
    W->>DB: 更新任务状态
```

### 后端技术栈

| 模块 | 技术 | 版本 | 说明 |
|------|------|------|------|
| Web 框架 | FastAPI | ^0.115 | 高性能异步 Web 框架，自动生成 API 文档 |
| 工作流引擎 | LangGraph | latest | 构建 RAG 处理流程图，支持条件分支 |
| 数据验证 | Pydantic | ^2.0 | 请求/响应模型验证 |
| ORM | SQLAlchemy | ^2.0 | MySQL 数据库操作 |
| 向量数据库 | OpenSearch | 2.x | 存储和检索文档向量，支持 hybrid search |
| 缓存 | Redis | ^5.0 | 会话缓存、Embedding 缓存 |
| 对象存储 | MinIO | ^7.2 | 文档文件存储，兼容 S3 API |
| 认证 | python-jose + bcrypt | - | JWT Token 认证，密码加密 |
| 文档解析 | pdfplumber + python-docx | - | PDF、Word 等格式解析 |
| HTTP 客户端 | httpx + aiohttp | - | 异步 HTTP 请求 |

### 前端技术栈

| 模块 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | Vue | ^3.4 | 组合式 API，响应式系统 |
| 构建工具 | Vite | ^5.0 | 快速开发和构建 |
| UI 组件（Admin） | Element Plus | ^2.6 | 管理后台界面组件库 |
| 路由 | Vue Router | ^4.3/5.0 | 单页应用路由管理 |
| Markdown 渲染 | Marked + Highlight.js | ^12.0 | 消息内容语法高亮 |
| HTTP 客户端 | axios（Admin） | ^1.6 | API 请求 |

## 项目结构

```
smart-ragflow/
├── start_all.py                 # 一键启动所有服务
├── pyproject.toml               # Python 项目配置
├── .env.example                 # 环境变量示例
├── .env                         # 本地环境变量（不提交到 git）
│
├── backend_QA/                  # 问答服务 (端口 8000)
│   ├── main.py                  # FastAPI 入口
│   ├── api/
│   │   ├── chat.py              # /v1/chat/completions 流式问答接口
│   │   ├── auth.py              # JWT 认证（注册/登录/登出）
│   │   ├── history.py           # 会话历史管理
│   │   └── download.py          # 文档下载接口
│   ├── core/
│   │   ├── graph.py             # LangGraph RAG 流程定义
│   │   ├── nodes.py             # 向量化/检索/重排序/生成节点
│   │   └── state.py             # 图状态定义
│   ├── services/
│   │   ├── llm.py               # LLM 客户端（OpenAI 兼容）
│   │   ├── opensearch.py        # 向量检索服务
│   │   ├── mmr.py               # MMR 重排序算法
│   │   ├── embedding.py         # Embedding 客户端
│   │   └── chat_history.py      # 对话历史管理
│   └── utils/
│       └── sse.py               # SSE 工具函数
│
├── backend_admin/               # 文档管理服务 (端口 8001)
│   ├── main.py                  # FastAPI 入口
│   ├── api/
│   │   └── documents.py         # 文档 CRUD 接口
│   ├── models/
│   │   └── __init__.py          # SQLAlchemy 模型（Document、ParseTask）
│   ├── database/
│   │   └── __init__.py          # 数据库连接配置
│   └── services/
│       └── document_service.py  # 文档业务逻辑
│
├── backend_parser/              # 文档解析服务 (Worker)
│   ├── worker.py                # 后台任务轮询主程序
│   ├── service.py               # DocumentParseService
│   ├── deepdoc_parser.py        # 文档解析器（PDF/Word/Excel等）
│   ├── chunker.py               # 文本分块（递归字符分块）
│   ├── embedding.py             # 向量化服务
│   ├── opensearch_client.py     # OpenSearch 客户端
│   ├── file_downloader.py       # 文件下载器
│   ├── tokenizer.py             # Tokenizer（tiktoken）
│   └── document_models.py       # 文档数据模型
│
├── backend_common/              # 公共模块
│   ├── clients/
│   │   ├── opensearch_client.py # OpenSearch 客户端封装
│   │   ├── redis_client.py      # Redis 客户端封装
│   │   ├── minio_client.py      # MinIO 客户端封装
│   │   └── embedding_client.py  # Embedding 客户端封装
│   ├── config.py                # 全局配置（pydantic-settings）
│   ├── models.py                # 共享数据库模型（User、ChatHistory等）
│   └── database.py              # 数据库连接池
│
├── frontend_QA/                 # 问答前端 (端口 3000)
│   ├── package.json             # npm 配置
│   ├── vite.config.js           # Vite 配置
│   ├── src/
│   │   ├── main.js              # 入口
│   │   ├── App.vue              # 根组件
│   │   ├── router.js            # 路由配置
│   │   ├── views/
│   │   │   ├── ChatView.vue     # 对话主界面（会话列表+聊天）
│   │   │   └── AuthView.vue     # 登录/注册界面
│   │   ├── components/
│   │   │   ├── ChatMessage.vue  # 消息气泡组件
│   │   │   ├── SessionItem.vue  # 会话列表项组件
│   │   │   └── FilePreview.vue  # 文件预览组件
│   │   └── utils/
│   │       ├── api.js           # API 客户端（SSE 流式处理）
│   │       └── auth.js          # 认证工具
│   └── dist/                    # 构建产物
│
├── frontend_admin/              # 管理后台前端 (端口 3001)
│   ├── package.json             # npm 配置
│   ├── vite.config.js           # Vite 配置
│   ├── src/
│   │   ├── main.js              # 入口
│   │   ├── App.vue              # 根组件
│   │   ├── views/
│   │   │   └── DocumentManager.vue  # 文档管理界面
│   │   └── api/
│   │       └── documents.js     # 文档 API 客户端
│   └── dist/                    # 构建产物
│
└── scripts/                     # 数据库脚本
    └── create_chat_history_table.sql  # 初始化 SQL
```

## 快速开始

### 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.10 | 后端运行环境 |
| Node.js | >= 18 | 前端构建环境 |
| MySQL | >= 8.0 | 业务数据存储 |
| OpenSearch | >= 2.0 | 向量检索引擎 |
| Redis | >= 6.0 | 会话缓存 |
| MinIO | latest | 文件存储 |

### 1. 克隆项目

```bash
git clone <repository-url>
cd smart-ragflow
```

### 2. 安装依赖

```bash
# 安装 Python 依赖（使用 uv 或 pip）
uv pip install -e .
# 或
pip install -e .

# 安装前端依赖
cd frontend_QA && npm install
cd ../frontend_admin && npm install
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、MinIO、OpenAI API 等
```

### 4. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE ragflow CHARACTER SET utf8mb4;"

# 执行初始化脚本（表结构会自动创建）
mysql -u root -p ragflow < scripts/create_chat_history_table.sql
```

### 5. 启动服务

#### 方式一：一键启动（推荐开发环境）

```bash
# 启动所有服务
python start_all.py

# 或分别启动
python start_all.py --services backend    # 仅启动后端
python start_all.py --services frontend   # 仅启动前端
```

#### 方式二：手动启动（生产环境）

```bash
# 1. 启动文档管理服务
uvicorn backend_admin.main:app --host 0.0.0.0 --port 8001

# 2. 启动问答服务
uvicorn backend_QA.main:app --host 0.0.0.0 --port 8000

# 3. 启动解析 Worker
python backend_parser/worker.py

# 4. 启动前端（新终端）
cd frontend_QA && npm run dev
cd frontend_admin && npm run dev
```

### 6. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 问答前端 | http://localhost:3000 | 用户对话界面 |
| 管理后台 | http://localhost:3001 | 文档管理界面 |
| QA API 文档 | http://localhost:8000/docs | FastAPI 自动生成的 Swagger |
| Admin API 文档 | http://localhost:8001/docs | FastAPI 自动生成的 Swagger |

## API 接口文档

### QA 服务接口

#### POST /v1/chat/completions
流式问答接口（OpenAI 兼容格式）

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| messages | array | 是 | 消息列表，每个消息包含 role 和 content |
| stream | boolean | 否 | 是否流式输出，默认 true |
| model | string | 否 | 模型名称，默认 deepseek-chat |
| temperature | float | 否 | 采样温度，默认 0.2 |
| session_id | string | 否 | 会话ID，用于关联历史对话 |

**请求示例：**

```json
{
  "messages": [
    {"role": "user", "content": "什么是 RAG？"}
  ],
  "stream": true,
  "model": "deepseek-chat",
  "session_id": "sess_xxx"
}
```

**响应示例（SSE 流式）：**

```
event: context_docs
data: {"docs": [{"index": 1, "title": "文档标题", "doc_id": "xxx"}]}

data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "RAG"}}]}
data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "是"}}]}
data: [DONE]
```

#### GET /v1/history/sessions
获取当前用户的会话列表

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | 否 | 返回条数，默认 50 |
| offset | integer | 否 | 偏移量，默认 0 |

#### GET /v1/history/sessions/{session_id}
获取指定会话的历史对话记录

#### DELETE /v1/history/sessions/{session_id}
删除指定会话

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

#### POST /auth/login
用户登录

**请求体：**

```json
{
  "username": "testuser",
  "password": "password123"
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
    "nickname": "测试用户"
  }
}
```

### Admin 服务接口

#### GET /api/documents
获取文档列表

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| size | integer | 否 | 每页数量，默认 10 |
| keyword | string | 否 | 搜索关键词 |
| status | integer | 否 | 状态筛选（0-未解析，1-解析中，2-失败，3-完成） |

#### POST /api/documents
上传文档

**请求体（multipart/form-data）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 上传的文件 |
| title | string | 否 | 文档标题 |
| description | string | 否 | 文档描述 |
| parse_immediately | boolean | 否 | 是否立即解析，默认 true |

#### DELETE /api/documents/{doc_id}
删除文档

#### PUT /api/documents/{doc_id}
更新文档信息

**请求体：**

```json
{
  "title": "新标题",
  "description": "新描述"
}
```

#### POST /api/documents/{doc_id}/parse
创建解析任务

#### GET /api/documents/{doc_id}/status
获取文档解析状态

## 配置说明

### 核心环境变量

```bash
# === LLM 配置 ===
OPENAI_API_KEY=sk-xxxxx                    # OpenAI API 密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1 # API 基础地址
OPENAI_MODEL=deepseek-chat                  # 模型名称

# === OpenSearch 配置 ===
OPENSEARCH_HOST=localhost                   # 主机地址
OPENSEARCH_PORT=9200                        # 端口
OPENSEARCH_INDEX=rag_docs                   # 索引名称
OPENSEARCH_USER=                            # 用户名（可选）
OPENSEARCH_PASSWORD=                        # 密码（可选）

# === 数据库配置 ===
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/ragflow?charset=utf8mb4

# === Redis 配置 ===
REDIS_URL=redis://localhost:6379/0          # Redis 连接 URL
REDIS_DB=0                                  # 数据库编号

# === MinIO 配置 ===
MINIO_ENDPOINT=localhost:9000               # 服务端点
MINIO_ACCESS_KEY=minioadmin                 # 访问密钥
MINIO_SECRET_KEY=minioadmin                 # 密钥
MINIO_BUCKET_NAME=smart-ragflow             # Bucket 名称
MINIO_SECURE=false                          # 是否使用 HTTPS

# === Embedding 配置 ===
EMBEDDING_MODEL=bge-m3                      # 嵌入模型名称
EMBEDDING_URL=http://localhost:11434/api/embeddings  # BGE-M3/Ollama 服务地址
EMBEDDING_DIM=1024                          # 向量维度
EMBEDDING_TIMEOUT=180                       # 超时时间（秒）

# === MMR 配置 ===
MMR_LAMBDA=0.5                              # 多样性权重（0-1）
MMR_TOP_K=5                                 # 返回文档数量

# === 分块配置 ===
CHUNK_SIZE=512                              # 分块大小
CHUNK_OVERLAP=100                           # 重叠大小
```

## 部署指南

### Docker 部署（推荐生产环境）

#### 1. 构建镜像

```bash
# 构建后端镜像
docker build -t smart-ragflow-backend -f docker/Dockerfile.backend .

# 构建前端镜像
docker build -t smart-ragflow-frontend-qa -f docker/Dockerfile.frontend.qa .
docker build -t smart-ragflow-frontend-admin -f docker/Dockerfile.frontend.admin .
```

#### 2. Docker Compose 部署

```bash
docker-compose up -d
```

### 生产环境建议

1. **使用反向代理**：Nginx 统一入口，配置 SSL/TLS
2. **数据库优化**：
   - MySQL 配置连接池
   - OpenSearch 配置分片和副本
   - 定期备份数据
3. **监控告警**：
   - 配置 OpenSearch、Redis、MinIO 监控
   - 设置日志收集（ELK 或 Loki）
4. **安全配置**：
   - 修改默认 JWT 密钥
   - 配置 CORS 白名单
   - 启用 MinIO 访问策略

## 开发指南

### 添加新的文档解析器

1. 在 `backend_parser/` 下实现新的解析器类，继承 `BaseParser`
2. 实现 `parse(file_path: str) -> str` 方法
3. 在 `deepdoc_parser.py` 中注册解析器

```python
from backend_parser.deepdoc_parser import register_parser

class CustomParser(BaseParser):
    def parse(self, file_path: str) -> str:
        # 实现解析逻辑
        return content

register_parser('custom', CustomParser)
```

### 自定义 RAG 流程

1. 修改 `backend_QA/core/nodes.py` 添加新节点
2. 在 `backend_QA/core/graph.py` 中调整流程图

```python
from langgraph.graph import StateGraph
from backend_QA.core.state import GraphState
from backend_QA.core.nodes import vectorize_node, custom_node

workflow = StateGraph(GraphState)
workflow.add_node("vectorize", vectorize_node)
workflow.add_node("custom", custom_node)
workflow.add_edge("vectorize", "custom")
# ...
```

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

## 数据库设计

### 核心表结构

#### users - 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| username | VARCHAR(50) | 用户名，唯一 |
| email | VARCHAR(100) | 邮箱，唯一 |
| password_hash | VARCHAR(255) | 密码哈希 |
| nickname | VARCHAR(50) | 昵称 |
| is_active | BOOLEAN | 是否激活 |
| is_admin | BOOLEAN | 是否管理员 |
| created_at | DATETIME | 创建时间 |

#### documents - 文档表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) | 主键，UUID |
| file_name | VARCHAR(255) | 文件名 |
| file_size | BIGINT | 文件大小 |
| file_md5 | VARCHAR(32) | 文件 MD5 |
| file_ext | VARCHAR(20) | 文件扩展名 |
| file_url | VARCHAR(500) | MinIO URL |
| parse_status | SMALLINT | 解析状态 |
| chunk_count | INT | 分块数量 |
| created_at | DATETIME | 创建时间 |

#### chat_history - 对话历史表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| user_id | BIGINT | 用户ID |
| session_id | VARCHAR(64) | 会话ID |
| role | VARCHAR(20) | 角色（user/assistant） |
| content | TEXT | 消息内容 |
| model | VARCHAR(50) | 模型名称 |
| tokens_used | INT | Token 数量 |
| created_at | DATETIME | 创建时间 |

## 常见问题

### Q: 文档解析失败怎么办？

A: 检查以下几点：
- Worker 是否正常启动：`ps aux | grep worker.py`
- MinIO 连接是否正常
- OpenSearch 索引是否存在
- 查看 Worker 日志获取详细错误信息

### Q: Embedding 服务连接失败？

A:
- 如果使用 Ollama，确保服务已启动：`ollama list`
- 如果使用 BGE-M3，确保服务地址正确
- 检查 `EMBEDDING_URL` 配置是否正确
- 测试连接：`curl http://localhost:11434/api/embeddings`

### Q: 前端无法连接后端？

A: 检查 CORS 配置，确保 `CORS_ORIGINS` 包含前端地址：
```bash
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

### Q: 如何调整 MMR 参数？

A: 修改环境变量：
```bash
MMR_LAMBDA=0.7      # 增大多样性
MMR_TOP_K=10        # 返回更多文档
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/xxx`
5. 创建 Pull Request

## 许可证

[MIT License](LICENSE)

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 工作流引擎
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Vue.js](https://vuejs.org/) - 前端框架
- [OpenSearch](https://opensearch.org/) - 搜索和分析引擎
- [Element Plus](https://element-plus.org/) - UI 组件库
