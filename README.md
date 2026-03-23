# Smart RAGFlow

智能问答系统，基于 RAG（检索增强生成）技术栈构建。

## 技术栈

- **Web 框架**: [FastAPI](https://fastapi.tiangolo.com/) - 高性能异步 Web 框架
- **ASGI 服务器**: [Uvicorn](https://www.uvicorn.org/) - 异步 ASGI 服务器
- **LLM 框架**: [LangChain](https://python.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) - 大语言模型应用开发框架
- **数据验证**: [Pydantic](https://docs.pydantic.dev/) - Python 数据验证库
- **搜索引擎**: [OpenSearch](https://opensearch.org/) - 分布式搜索和分析引擎
- **缓存**: [Redis](https://redis.io/) - 内存数据结构存储
- **对象存储**: [MinIO](https://min.io/) - 高性能对象存储
- **向量化**: BGE-M3 - 文本嵌入模型

## 项目结构

```
smart-ragflow/
├── client/                 # 主应用包
│   ├── api/               # API 路由
│   │   ├── __init__.py
│   │   └── chat.py        # 问答流式接口
│   ├── core/              # 核心逻辑
│   │   ├── __init__.py
│   │   ├── graph.py       # LangGraph 状态图定义
│   │   ├── nodes.py       # 图节点函数（向量化、检索、重排序、LLM）
│   │   └── state.py       # 状态定义（TypedDict）
│   ├── services/          # 外部服务封装
│   │   ├── __init__.py
│   │   ├── embedding.py   # BGE-M3 HTTP 客户端
│   │   ├── opensearch.py  # OpenSearch 混合检索封装
│   │   ├── llm.py         # LLM 客户端（支持流式）
│   │   └── mmr.py         # MMR 重排序实现
│   ├── utils/             # 工具函数
│   │   ├── __init__.py
│   │   └── sse.py         # SSE 流式响应辅助函数
│   ├── __init__.py
│   └── main.py            # FastAPI 应用入口
├── .env.example           # 环境变量模板
├── .gitignore             # Git 忽略配置
├── pyproject.toml         # 项目配置与依赖
├── uv.lock                # 依赖锁定文件
└── README.md              # 项目说明
```

## 快速启动

### 1. 环境准备

确保已安装 [uv](https://docs.astral.sh/uv/)（Python 包管理器）。

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写实际的配置值
```

必需的环境变量：
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` - LLM API 配置
- `EMBEDDING_URL` - BGE-M3 嵌入服务地址
- `OPENSEARCH_HOST` / `OPENSEARCH_PORT` / `OPENSEARCH_INDEX` - OpenSearch 配置

### 4. 启动服务

```bash
uv run uvicorn client.main:app --reload
```

服务启动后，访问 http://localhost:8000/docs 查看 API 文档。

## API 接口

### POST /v1/chat/completions

智能问答流式接口，支持 OpenAI 风格的 SSE 流式输出。

**请求体：**
```json
{
  "messages": [
    {"role": "user", "content": "你的问题"}
  ],
  "stream": true,
  "model": "gpt-3.5-turbo"
}
```

**响应格式（SSE）：**
```
data: {"id": "chatcmpl-xxx", "object": "chat.completion.chunk", ...}
data: {"id": "chatcmpl-xxx", "object": "chat.completion.chunk", ...}
data: [DONE]
```

## RAG 处理流程

1. **向量化** - 使用 BGE-M3 将问题转换为 1024 维向量
2. **混合检索** - 在 OpenSearch 中执行 BM25 + 向量相似度检索，返回 Top 10
3. **MMR 重排序** - 执行最大边际相关性算法，取 Top 5（平衡相关性和多样性）
4. **LLM 生成** - 组装 Prompt，调用 LLM 流式生成答案

## 开发规范

- 所有 Python 文件使用 `from ... import ...` 绝对导入
- 函数、类需添加 docstring 说明
- 异步优先：HTTP 客户端、数据库操作均使用异步库
- 错误处理：捕获异常并记录日志
- 日志记录：使用 logging 记录关键步骤
