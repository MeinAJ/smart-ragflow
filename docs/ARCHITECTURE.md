# Smart RAGFlow 架构文档

> 本文档深入解析 Smart RAGFlow 的系统架构、模块设计和数据流转，帮助开发者理解系统内部工作原理。

## 目录

- [系统概览](#系统概览)
- [架构设计原则](#架构设计原则)
- [核心模块详解](#核心模块详解)
- [数据流转图](#数据流转图)
- [技术选型说明](#技术选型说明)
- [扩展点设计](#扩展点设计)

---

## 系统概览

### 什么是 RAG？

RAG（Retrieval-Augmented Generation，检索增强生成）是一种将大语言模型（LLM）与外部知识库结合的架构模式：

```
用户问题 → 向量化 → 检索相关文档 → 构建上下文 → LLM 生成答案
```

**为什么需要 RAG？**

- **解决知识时效性**：LLM 训练数据有截止日期，RAG 可以接入最新文档
- **减少幻觉**：基于检索到的真实文档生成答案，而非模型编造
- **可追溯性**：可以展示答案来源，提高可信度
- **成本效益**：无需微调模型，只需更新知识库

### Smart RAGFlow 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                         │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │  Frontend QA    │  │ Frontend Admin  │                      │
│  │  (Port 3000)    │  │ (Port 3001)     │                      │
│  │  Vue3 + Vite    │  │ Element Plus    │                      │
│  └────────┬────────┘  └────────┬────────┘                      │
└───────────┼────────────────────┼────────────────────────────────┘
            │ HTTP               │ HTTP
┌───────────┼────────────────────┼────────────────────────────────┐
│           ▼                    ▼                               │
│  ┌─────────────────┐  ┌─────────────────┐      API 网关层       │
│  │  Backend QA     │  │  Backend Admin  │                      │
│  │  (Port 8000)    │  │  (Port 8001)    │                      │
│  │  FastAPI        │  │  FastAPI        │                      │
│  │  RAG 流程处理    │  │  文档管理       │                      │
│  └────────┬────────┘  └────────┬────────┘                      │
└───────────┼────────────────────┼────────────────────────────────┘
            │                    │
            │         ┌──────────┘
            │         │ 创建任务
            ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     核心处理层 (Core)                            │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │  LangGraph      │  │  Parser Worker  │                      │
│  │  RAG 工作流引擎  │  │  文档解析服务    │                      │
│  │  · 向量化节点    │  │  · 文件下载     │                      │
│  │  · 检索节点      │  │  · 文档解析     │                      │
│  │  · 重排序节点    │  │  · 文本分块     │                      │
│  │  · 生成节点      │  │  · 向量化       │                      │
│  └─────────────────┘  └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     存储层 (Storage)                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ OpenSearch  │ │   MySQL     │ │   Redis     │ │  MinIO    │ │
│  │ 向量+全文    │ │  业务数据    │ │  会话缓存    │ │ 文件存储   │ │
│  │  hybrid     │ │  用户/文档   │ │  历史记录    │ │           │ │
│  │  search     │ │  任务状态    │ │  Embedding  │ │           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 架构设计原则

### 1. 微服务分离

系统将功能拆分为独立服务，每个服务有明确的职责：

| 服务 | 职责 | 端口 | 独立部署 |
|------|------|------|----------|
| Backend QA | 处理用户问答请求，执行 RAG 流程 | 8000 | ✓ |
| Backend Admin | 管理文档、用户、系统配置 | 8001 | ✓ |
| Parser Worker | 后台异步处理文档解析任务 | - | ✓ |
| Frontend QA | 用户对话界面 | 3000 | ✓ |
| Frontend Admin | 管理员界面 | 3001 | ✓ |

**设计理由**：
- QA 服务需要高并发、低延迟，可与 Admin 服务独立扩容
- Parser Worker 是计算密集型，可单独水平扩展
- 前后端分离，前端可独立迭代部署

### 2. 异步任务处理

文档解析是耗时操作（可能长达数分钟），采用异步处理模式：

```
用户上传 → 保存文件 → 创建任务 → 立即返回
                                      ↓
                              Worker 轮询 → 下载 → 解析 → 索引
```

**状态流转**：
```
PENDING(0) → WAITING(1) → PARSING(2) → COMPLETED(3)
                              ↓
                           FAILED(4)
```

### 3. 无状态设计

QA 服务是无状态的，会话信息存储在 Redis：

- **优势**：服务可随时重启、水平扩展
- **实现**：`session_id` + Redis Hash 存储对话历史

### 4. 可插拔组件

Embedding、LLM、存储等组件通过接口抽象，支持替换：

```python
# Embedding 客户端接口
class EmbeddingClient:
    async def embed(self, text: str) -> List[float]: ...

# 可实现不同的客户端
class BGEM3Client(EmbeddingClient): ...
class OllamaClient(EmbeddingClient): ...
class OpenAIClient(EmbeddingClient): ...
```

---

## 核心模块详解

### 1. LangGraph RAG 工作流

位于 `backend_QA/core/`，使用 LangGraph 构建 RAG 处理流程：

#### 1.1 状态定义 (`state.py`)

```python
class GraphState(TypedDict):
    question: str           # 用户问题
    question_vector: List[float]  # 问题向量
    retrieved_docs: List[dict]    # 检索结果
    reranked_docs: List[dict]     # 重排序结果
    answer: Optional[str]         # 最终答案
    error: Optional[str]          # 错误信息
```

**设计意图**：使用 `TypedDict` 明确状态流转的数据结构，便于类型检查和 IDE 提示。

#### 1.2 节点实现 (`nodes.py`)

每个节点是纯函数，接收状态并返回更新片段：

```
vectorize_node: 问题 → 向量
    ↓
retrieve_node: 向量 → 候选文档（BM25 + KNN）
    ↓
rerank_node: 候选文档 → 精选文档（MMR）
    ↓
generate_node: 精选文档 → 答案
```

**节点设计模式**：
```python
async def node_name(state: GraphState) -> Dict[str, Any]:
    """
    节点函数签名统一：
    - 输入：完整状态
    - 输出：状态更新片段（部分字段）
    - 错误处理：返回 {"error": "..."}
    """
    try:
        # 处理逻辑
        return {"field_name": value}
    except Exception as e:
        return {"error": str(e)}
```

#### 1.3 流程编排 (`graph.py`)

```python
workflow = StateGraph(GraphState)

# 添加节点
workflow.add_node("vectorize", vectorize_node)
workflow.add_node("retrieve", retrieve_node)
...

# 设置入口
workflow.set_entry_point("vectorize")

# 条件边：根据 should_continue 决定下一步
workflow.add_conditional_edges(
    "vectorize",
    should_continue,  # 检查 state.get("error")
    {
        "continue": "retrieve",
        "error_handler": "error_handler"
    }
)
```

**为什么用 LangGraph？**

| 特性 | 优势 |
|------|------|
| 可视化流程 | 代码即文档，流程清晰 |
| 条件分支 | 灵活处理错误和特殊情况 |
| 状态管理 | 显式状态流转，易于调试 |
| 异步支持 | 原生支持 async/await |

### 2. 混合检索 (Hybrid Search)

位于 `backend_QA/services/opensearch.py`，结合 BM25 和向量检索：

```python
async def hybrid_search(
    self, 
    query_text: str,      # BM25 查询文本
    query_vector: List[float],  # KNN 查询向量
    size: int = 10
) -> List[dict]:
    """
    混合检索 = BM25 全文检索 + KNN 向量检索
    
    为什么需要混合？
    - BM25：擅长精确匹配、关键词搜索
    - KNN：擅长语义匹配、同义词理解
    - 结合：两者互补，提高召回率
    """
```

**OpenSearch 查询结构**：

```json
{
  "query": {
    "bool": {
      "should": [
        {
          "multi_match": {
            "query": "用户问题",
            "fields": ["content^1.0", "title^2.0"],
            "type": "best_fields"
          }
        },
        {
          "knn": {
            "vector_field": {
              "vector": [0.1, 0.2, ...],
              "k": 10
            }
          }
        }
      ]
    }
  }
}
```

**权重配置**（`backend_common/config.py`）：

```python
SEARCH_TEXT_BOOST = 1.0     # 正文权重
SEARCH_TITLE_BOOST = 2.0    # 标题权重（标题匹配更重要）
SEARCH_MIN_SCORE = 0.4      # 最低相似度阈值
```

### 3. MMR 重排序

位于 `backend_QA/services/mmr.py`，解决检索结果冗余问题：

```python
def mmr_rerank(
    query_vector: List[float],
    documents: List[dict],
    lambda_param: float = 0.7,  # 多样性权重
    top_k: int = 5
) -> List[dict]:
    """
    MMR (Maximal Marginal Relevance) 算法
    
    公式：MMR = λ * Sim(query, doc) - (1-λ) * max Sim(doc, selected)
    
    - λ = 1.0：只考虑相关性，不考虑多样性
    - λ = 0.0：只考虑多样性，不考虑相关性
    - λ = 0.5~0.7：平衡相关性和多样性（推荐）
    """
```

**应用场景**：

用户问："Python 的并发编程"

| 传统排序 (Top-5) | MMR 排序 (λ=0.7) |
|-----------------|-----------------|
| 5 篇都是 threading | threading、asyncio、multiprocessing、concurrent.futures、gevent |
| 内容重复 | 覆盖不同方案 |

### 4. Parser Worker 文档处理

位于 `backend_parser/`，后台异步处理文档：

#### 4.1 处理流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  下载文件 │ → │ 解析文档  │ → │ 文本分块  │ → │ 向量化   │ → │ 索引入库  │
│ MinIO   │    │ DeepDoc  │    │ Chunker  │    │ Embedding│    │ OpenSearch│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

#### 4.2 文档解析器 (`deepdoc_parser.py`)

支持格式：

| 格式 | 库 | 处理方式 |
|------|-----|----------|
| PDF | pdfplumber | 提取文本和页面信息 |
| Word | python-docx | 提取段落和标题样式 |
| Excel | openpyxl | 提取表格数据 |
| PPT | python-pptx | 提取幻灯片文本 |
| Markdown | 内置 | 解析标题层级 |
| HTML | BeautifulSoup | 清理标签，提取正文 |
| TXT | 内置 | 直接读取 |

#### 4.3 文本分块 (`chunker.py`)

```python
class RecursiveCharacterChunker:
    """
    递归字符分块器
    
    策略：
    1. 优先按段落分隔（\n\n）
    2. 段落太长则按句子（\n）
    3. 句子太长则按标点（。；）
    4. 最后按字符切分
    
    保留上下文：相邻块有 overlap 重叠区域
    """
```

**分块配置**：
```python
CHUNK_SIZE = 512        # 目标块大小（token 数）
CHUNK_OVERLAP = 100     # 相邻块重叠大小
```

### 5. 存储层设计

#### 5.1 OpenSearch 索引结构

```json
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "analyzer": "ik_max_word"     // 中文分词
      },
      "title": {
        "type": "text",
        "analyzer": "ik_max_word",
        "boost": 2.0                   // 标题权重
      },
      "vector": {
        "type": "knn_vector",
        "dimension": 1024             // BGE-M3 维度
      },
      "doc_id": { "type": "keyword" },
      "file_name": { "type": "keyword" },
      "chunk_index": { "type": "integer" },
      "created_at": { "type": "date" }
    }
  }
}
```

#### 5.2 MySQL 表结构

```sql
-- 用户表
users (id, username, email, password_hash, created_at)

-- 文档表
documents (id, file_name, file_size, file_md5, file_url, 
           parse_status, chunk_count, created_at)

-- 解析任务表
parse_tasks (id, doc_id, status, file_url, error_message,
             started_at, completed_at)

-- 对话历史表
chat_history (id, user_id, session_id, role, content,
              model, tokens_used, created_at)
```

#### 5.3 Redis 数据设计

```
# 对话历史（Hash）
rag:session:{session_id}
├── messages (JSON 字符串)
└── updated_at (时间戳)

# Embedding 缓存（String）
emb:{md5_hash} = [0.1, 0.2, ...]

# 会话列表（Sorted Set）
rag:user_sessions:{user_id}
├── score: timestamp
└── member: session_id
```

---

## 数据流转图

### 1. 问答流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend QA                                             │
│ 1. 收集 messages（包含历史）                             │
│ 2. 提取最后一条 user 消息作为 question                   │
│ 3. 发送 POST /v1/chat/completions                       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Backend QA (FastAPI)                                    │
│ 1. JWT 认证验证用户身份                                  │
│ 2. 从 Redis 获取历史对话 context                         │
│ 3. 调用 stream_rag_with_context()                        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ RAG Pipeline (LangGraph)                                │
│                                                         │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │ 1. Vectorize │→│ 2. Retrieve  │→│ 3. Rerank    │   │
│ │              │  │  (Hybrid)    │  │   (MMR)      │   │
│ │ 问题 → 向量   │  │ BM25 + KNN   │  │ λ=0.7        │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│                                      │                  │
│                                      ▼                  │
│                              ┌──────────────┐          │
│                              │ 4. Generate  │          │
│                              │  LLM 流式生成 │          │
│                              │ 附带 context │          │
│                              └──────────────┘          │
└─────────────────────────────────────────────────────────┘
    │
    ▼ (SSE 流式返回)
事件: context_docs → 前端显示引用文档
事件: data (chunk) → 前端显示文本
事件: [DONE]       → 完成
    │
    ▼
后端保存对话历史到 Redis
```

### 2. 文档处理流程

```
用户上传文档
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend Admin                                          │
│ POST /api/documents (multipart/form-data)               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Backend Admin (FastAPI)                                 │
│ 1. 保存文件到 MinIO                                      │
│ 2. 创建 Document 记录（status=0）                        │
│ 3. 创建 ParseTask 记录（status=1）                       │
│ 4. 返回 doc_id                                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼ (异步处理)
┌─────────────────────────────────────────────────────────┐
│ Parser Worker (轮询任务)                                 │
│                                                         │
│ while True:                                             │
│   task = get_waiting_task()  # 乐观锁获取               │
│   if task:                                              │
│       process_task(task)                                │
│   else:                                                 │
│       sleep(5)                                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ DocumentParseService                                    │
│                                                         │
│ 1. download_file()    → 从 MinIO 下载                   │
│ 2. parse()            → DeepDocParser 解析              │
│ 3. chunk()            → RecursiveCharacterChunker       │
│ 4. embed()            → EmbeddingClient 向量化          │
│ 5. index()            → OpenSearchStore 索引            │
│                                                         │
│ 更新 task status = 3 (完成) 或 4 (失败)                 │
└─────────────────────────────────────────────────────────┘
```

---

## 技术选型说明

### 为什么选 FastAPI？

| 特性 | 说明 |
|------|------|
| 异步原生 | async/await 支持高并发 |
| 自动文档 | 自动生成 OpenAPI/Swagger UI |
| 类型检查 | Pydantic 模型验证 |
| 生态丰富 | 中间件、依赖注入、后台任务 |

### 为什么选 LangGraph？

| 特性 | 说明 |
|------|------|
| 流程可视化 | 代码即流程图 |
| 状态管理 | 显式状态流转 |
| 调试友好 | 可查看每个节点的输入输出 |
| 扩展性 | 易于添加新节点 |

### 为什么选 OpenSearch？

| 特性 | 说明 |
|------|------|
| 开源 | Apache 2.0 协议 |
| Hybrid Search | 原生支持 BM25 + KNN 混合查询 |
| 向量检索 | 内置 k-NN 插件 |
| 阿里云支持 | 云服务兼容性好 |

### 为什么选 BGE-M3？

| 特性 | 说明 |
|------|------|
| 多语言 | 支持 100+ 语言 |
| 高性能 | 1024 维度，检索准确率高 |
| 开源 | MIT 协议，可商用 |
| 本地部署 | 无需调用外部 API |

---

## 扩展点设计

### 1. 添加新的文档解析器

```python
# backend_parser/parsers/custom_parser.py
from backend_parser.deepdoc_parser import BaseParser

class CustomParser(BaseParser):
    def parse(self, file_path: str) -> str:
        # 实现解析逻辑
        return content

# 注册解析器
# 在 backend_parser/deepdoc_parser.py 中添加
PARSERS[".custom"] = CustomParser()
```

### 2. 自定义 RAG 节点

```python
# backend_QA/core/nodes.py

async def custom_node(state: GraphState) -> Dict[str, Any]:
    """
    自定义处理节点示例：实体识别
    """
    question = state["question"]
    
    # 调用 NER 服务识别实体
    entities = await ner_service.extract(question)
    
    return {"entities": entities}

# 在 graph.py 中添加到流程
workflow.add_node("ner", custom_node)
workflow.add_edge("vectorize", "ner")
workflow.add_edge("ner", "retrieve")
```

### 3. 替换 Embedding 服务

```python
# backend_QA/services/embedding.py

class CustomEmbeddingClient:
    """自定义 Embedding 客户端"""
    
    async def embed(self, text: str) -> List[float]:
        # 调用自定义服务
        response = await self.client.post("/embed", json={"text": text})
        return response.json()["embedding"]

# 替换全局实例
embedding_client = CustomEmbeddingClient()
```

### 4. 添加自定义检索策略

```python
# backend_QA/services/opensearch.py

async def semantic_search_with_filter(
    self,
    query_vector: List[float],
    doc_ids: List[str],  # 限定搜索范围
    size: int = 10
) -> List[dict]:
    """
    在指定文档集合中进行语义搜索
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"knn": {"vector": {"vector": query_vector, "k": size}}},
                    {"terms": {"doc_id": doc_ids}}  # 限定范围
                ]
            }
        }
    }
    return await self.search(query)
```

---

## 性能优化建议

### 1. Embedding 缓存

```python
# 已实现于 backend_QA/services/embedding.py

async def embed(self, text: str) -> List[float]:
    # 1. 计算文本 MD5
    cache_key = f"emb:{md5(text)}"
    
    # 2. 查 Redis 缓存
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 3. 调用服务
    vector = await self._call_embedding_service(text)
    
    # 4. 写入缓存（10天）
    await redis.setex(cache_key, 864000, json.dumps(vector))
    
    return vector
```

**效果**：相同问题/文档的 Embedding 只需计算一次，减少 90%+ 的 Embedding 调用。

### 2. 对话历史裁剪

```python
# backend_QA/services/chat_history.py

async def get_context_with_trim(
    self, 
    user_id: int, 
    session_id: str,
    max_tokens: int = 2000  # 限制历史 Token 数
) -> List[dict]:
    """
    获取历史对话，超过阈值时裁剪早期消息
    """
```

**原因**：LLM 有上下文长度限制，且历史越长响应越慢。

### 3. 连接池配置

```python
# MySQL 连接池
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # 常驻连接数
    max_overflow=10,      # 最大溢出连接
    pool_pre_ping=True    # 连接健康检查
)

# Redis 连接池
redis_client = redis.Redis(
    host=host,
    port=port,
    max_connections=50,   # 最大连接数
    socket_keepalive=True
)
```

---

## 故障排查指南

### 常见问题及定位

| 问题 | 可能原因 | 排查方法 |
|------|----------|----------|
| 问答无响应 | LLM 服务异常 | 检查 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` |
| 检索不到文档 | OpenSearch 索引为空 | 检查文档是否已解析完成（status=3） |
| 解析失败 | Parser Worker 未启动 | `ps aux \| grep worker.py` |
| 上传失败 | MinIO 连接异常 | 检查 MinIO 服务状态和配置 |
| 历史记录丢失 | Redis 连接异常 | 检查 Redis 服务和 `REDIS_URL` |

### 日志定位

```bash
# 查看各服务日志
tail -f logs/qa_api.log        # QA 服务
tail -f logs/admin_api.log     # Admin 服务
tail -f logs/parser_worker.log # Worker

# 按关键词过滤
grep "ERROR" logs/*.log
grep "Vectorize node" logs/qa_api.log
```

---

## 总结

Smart RAGFlow 的架构设计遵循以下核心思想：

1. **微服务解耦**：各服务独立部署、独立扩展
2. **异步处理**：耗时操作后台化，提高响应速度
3. **无状态设计**：服务状态外置，支持水平扩展
4. **可插拔组件**：核心组件通过接口抽象，易于替换
5. **分层清晰**：表现层、API层、核心层、存储层职责明确

理解这些设计原则，有助于你在定制开发时做出正确的架构决策。
