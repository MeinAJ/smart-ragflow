# Smart RAGFlow

智能问答系统框架，基于 RAG（Retrieval-Augmented Generation）技术构建，提供完整的文档管理、智能解析和问答服务。

## 功能特性

### 核心功能
- **📄 文档解析**：支持 PDF、Word、TXT、Markdown、HTML 等多种格式
- **🔍 智能检索**：基于 OpenSearch 的向量检索 + 文本检索混合搜索
- **🤖 AI 问答**：支持流式输出的智能问答，兼容 OpenAI API 格式
- **📚 文档管理**：完整的文档上传、解析、存储和检索生命周期管理
- **💬 对话历史**：支持多轮对话，自动保存和管理聊天历史

### 系统架构
```
┌─────────────────────────────────────────────────────────────────┐
│                         Smart RAGFlow                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Frontend QA   │  Frontend Admin │      Backend Services       │
│    (Port 3000)  │   (Port 3001)   │                             │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         └─────────────────┼───────────────────────┘
                           ▼
         ┌─────────────────────────────────────────┐
         │           API Gateway                   │
         │  • QA API (Port 8000)                   │
         │  • Admin API (Port 8001)                │
         └─────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐    ┌─────────────┐    ┌──────────────┐
   │  Parser  │    │   RAG Core  │    │    Auth      │
   │  Worker  │    │  LangGraph  │    │   Service    │
   └──────────┘    └─────────────┘    └──────────────┘
         │                 │
         ▼                 ▼
   ┌─────────────────────────────────────────────────┐
   │              Infrastructure Layer               │
   │  • OpenSearch (向量存储)                         │
   │  • Redis (缓存 & 消息队列)                       │
   │  • MinIO (对象存储)                             │
   │  • MySQL (关系数据库)                           │
   └─────────────────────────────────────────────────┘
```

## 项目结构

```
smart-ragflow/
├── start_all.py              # 一键启动所有服务
├── pyproject.toml            # 项目配置和依赖
├── .env                      # 环境变量配置
├── .env.example              # 环境变量示例
│
├── backend_QA/               # 问答服务后端 (Port 8000)
│   ├── main.py               # FastAPI 主入口
│   ├── api/
│   │   ├── chat.py           # 聊天/问答 API
│   │   ├── auth.py           # 认证接口
│   │   ├── history.py        # 历史记录接口
│   │   └── download.py       # 文件下载接口
│   ├── core/
│   │   ├── graph.py          # LangGraph RAG 工作流
│   │   ├── nodes.py          # 工作流节点定义
│   │   └── state.py          # 状态定义
│   └── services/
│       ├── llm.py            # LLM 客户端
│       ├── opensearch.py     # 搜索服务
│       └── chat_history.py   # 对话历史服务
│
├── backend_admin/            # 管理后台后端 (Port 8001)
│   ├── main.py               # FastAPI 主入口
│   ├── api/
│   │   └── documents.py      # 文档管理 API
│   ├── models/               # SQLAlchemy 模型
│   └── services/
│       └── document_service.py
│
├── backend_parser/           # 文档解析服务
│   ├── service.py            # 解析服务主入口
│   ├── deepdoc_parser.py     # 文档解析器
│   ├── chunker.py            # 文档分块
│   ├── embedding.py          # 向量嵌入
│   ├── opensearch_client.py  # OpenSearch 客户端
│   ├── worker.py             # 后台工作进程
│   └── cli.py                # 命令行工具
│
├── backend_common/           # 公共模块
│   ├── config.py             # 全局配置
│   ├── models.py             # 共享模型
│   ├── database.py           # 数据库连接
│   └── clients/              # 各种客户端封装
│       ├── embedding_client.py
│       ├── opensearch_client.py
│       ├── redis_client.py
│       └── minio_client.py
│
├── frontend_QA/              # 问答前端 (Port 3000)
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│
├── frontend_admin/           # 管理后台前端 (Port 3001)
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│
└── docs/                     # 项目文档
```

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- MySQL >= 8.0
- Redis >= 6.0
- OpenSearch >= 2.0
- MinIO (可选，用于文件存储)

### 安装依赖

```bash
# 安装 Python 依赖
pip install -e .

# 或使用 uv
uv sync

# 安装前端依赖
cd frontend_QA && npm install
cd ../frontend_admin && npm install
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置各项服务连接信息
```

### 启动服务

```bash
# 一键启动所有服务
python start_all.py

# 或分别启动
python start_all.py --services backend    # 只启动后端服务
python start_all.py --services frontend   # 只启动前端服务

# 单独启动特定服务
python start_all.py --services admin      # 管理后台 API
python start_all.py --services qa         # 问答 API
python start_all.py --services parser     # 解析服务
python start_all.py --services frontend_qa    # 问答前端
python start_all.py --services frontend_admin # 管理后台前端
```

服务启动后：
- 问答前端: http://localhost:3000
- 管理后台: http://localhost:3001
- 问答 API: http://localhost:8000
- 管理 API: http://localhost:8001

## RAG 流程说明

系统采用 LangGraph 构建 RAG 工作流，流程如下：

```
用户提问
    │
    ▼
┌─────────────┐
│ Vectorize   │  ← 问题向量化
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Retrieve   │  ← 向量 + 文本混合检索
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Rerank    │  ← MMR 重排序，保证多样性
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Generate   │  ← LLM 生成答案（流式输出）
└──────┬──────┘
       │
       ▼
   返回答案
```

## API 接口

### 问答接口

**POST /v1/chat/completions**

兼容 OpenAI API 格式的流式问答接口。

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "messages": [{"role": "user", "content": "什么是 RAG？"}],
    "stream": true,
    "session_id": "session_123"
  }'
```

### 文档管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/documents | 上传文档 |
| GET | /api/documents | 获取文档列表 |
| GET | /api/documents/{id} | 获取文档详情 |
| DELETE | /api/documents/{id} | 删除文档 |
| POST | /api/documents/{id}/parse | 触发文档解析 |

## 配置说明

### 核心配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥 | - |
| `OPENAI_BASE_URL` | LLM API 地址 | https://api.openai.com/v1 |
| `OPENAI_MODEL` | 模型名称 | gpt-3.5-turbo |
| `OPENSEARCH_HOST` | OpenSearch 主机 | localhost |
| `OPENSEARCH_PORT` | OpenSearch 端口 | 9200 |
| `REDIS_URL` | Redis 连接 URL | redis://localhost:6379 |
| `EMBEDDING_URL` | Embedding 服务地址 | - |
| `EMBEDDING_MODEL` | 嵌入模型名称 | bge-m3 |
| `MINIO_ENDPOINT` | MinIO 服务端点 | localhost:9000 |
| `DATABASE_URL` | MySQL 连接 URL | - |

## 文档解析流程

```
文件上传
    │
    ▼
MinIO 存储
    │
    ▼
Parser Worker 处理
    │
    ├── 下载文件
    ├── 解析文档 (PDF/Word/TXT/MD/HTML)
    ├── 文档分块 (Chunking)
    ├── 生成向量 (Embedding)
    └── 存储到 OpenSearch
    │
    ▼
可检索的知识库
```

## 开发指南

### 添加新的文档解析器

在 `backend_parser/deepdoc_parser.py` 中添加新的解析方法：

```python
def _parse_new_format(self, file_path: Path) -> ParseResult:
    # 实现解析逻辑
    pass
```

### 自定义 RAG 节点

在 `backend_QA/core/nodes.py` 中添加自定义节点：

```python
async def custom_node(state: GraphState) -> dict:
    # 实现节点逻辑
    return {"key": value}
```

然后在 `backend_QA/core/graph.py` 中添加到工作流。

## 技术栈

- **后端**: FastAPI, LangChain, LangGraph, SQLAlchemy
- **前端**: Vue 3, Vite
- **向量数据库**: OpenSearch
- **缓存**: Redis
- **对象存储**: MinIO
- **关系数据库**: MySQL

## 许可证

MIT License
