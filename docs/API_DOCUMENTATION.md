# Smart RAGFlow API 文档

> 完整的 API 接口参考文档，包含请求/响应格式、示例代码和错误处理。

## 目录

- [认证说明](#认证说明)
- [QA 服务 API](#qa-服务-api)
- [Admin 服务 API](#admin-服务-api)
- [错误处理](#错误处理)
- [限流说明](#限流说明)

---

## 认证说明

### JWT Token 认证

除登录/注册接口外，所有接口都需要在请求头中携带 JWT Token：

```http
Authorization: Bearer <your_jwt_token>
```

### 获取 Token

通过登录接口获取：

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

**响应**：
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

**Token 有效期**：7 天

---

## QA 服务 API

Base URL: `http://localhost:8000`

### 1. 智能问答（流式）

**端点**：`POST /v1/chat/completions`

**功能**：接收用户问题，基于 RAG 流程生成流式回答

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| messages | array | 是 | 消息列表，每个消息包含 role 和 content |
| messages[].role | string | 是 | 角色：`system`/`user`/`assistant` |
| messages[].content | string | 是 | 消息内容 |
| stream | boolean | 否 | 是否流式输出，默认 `true` |
| model | string | 否 | 模型名称，默认 `deepseek-chat` |
| temperature | float | 否 | 采样温度（0-2），默认 `0.2` |
| session_id | string | 否 | 会话ID，用于关联历史对话 |

#### 请求示例

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "messages": [
      {"role": "user", "content": "什么是 RAG 技术？"}
    ],
    "stream": true,
    "model": "deepseek-chat",
    "session_id": "sess_abc123"
  }'
```

#### 流式响应（SSE）

```
event: context_docs
data: {"docs": [{"index": 1, "title": "RAG技术介绍.pdf", "doc_id": "doc_xxx"}]}

data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "RAG"}}]}
data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "（检索增强生成）"}}]}
data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "是一种结合"}}]}
...
data: [DONE]
```

#### 响应事件说明

| 事件类型 | 说明 | 数据格式 |
|----------|------|----------|
| `context_docs` | 返回引用的文档元数据 | `{"docs": [...]}` |
| `data` | 生成的文本片段（OpenAI 格式） | `{"id": "...", "choices": [...]}` |
| `error` | 处理错误 | `{"message": "..."}` |
| `[DONE]` | 流结束标记 | - |

#### context_docs 数据结构

```json
{
  "docs": [
    {
      "index": 1,
      "doc_id": "doc_abc123",
      "title": "RAG技术介绍",
      "file_name": "rag_intro.pdf",
      "doc_url": "http://localhost:9000/...",
      "metadata": {
        "chunk_index": 0,
        "score": 0.89
      }
    }
  ]
}
```

---

### 2. 用户注册

**端点**：`POST /auth/register`

**功能**：创建新用户账号

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（2-50字符） |
| password | string | 是 | 密码（6-100字符） |
| email | string | 是 | 邮箱地址 |
| nickname | string | 否 | 昵称 |

#### 请求示例

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepass123",
    "email": "newuser@example.com",
    "nickname": "新用户"
  }'
```

#### 响应示例（成功）

```json
{
  "id": 123,
  "username": "newuser",
  "email": "newuser@example.com",
  "nickname": "新用户",
  "created_at": "2024-01-15T10:30:00"
}
```

#### 错误响应

```json
{
  "detail": "Username already exists"
}
```

---

### 3. 用户登录

**端点**：`POST /auth/login`

**功能**：用户认证，返回 JWT Token

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

#### 请求示例

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

#### 响应示例

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": 1,
    "username": "testuser",
    "nickname": "测试用户",
    "is_admin": false
  }
}
```

---

### 4. 获取会话列表

**端点**：`GET /v1/history/sessions`

**功能**：获取当前用户的所有会话列表

#### 查询参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | 否 | 返回条数，默认 50，最大 100 |
| offset | integer | 否 | 偏移量，默认 0 |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/v1/history/sessions?limit=20&offset=0" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "total": 15,
  "sessions": [
    {
      "session_id": "sess_abc123",
      "title": "什么是 RAG 技术？",
      "message_count": 5,
      "last_message_at": "2024-01-15T10:30:00",
      "created_at": "2024-01-15T10:00:00"
    }
  ]
}
```

---

### 5. 获取会话详情

**端点**：`GET /v1/history/sessions/{session_id}`

**功能**：获取指定会话的历史消息记录

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话ID |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/v1/history/sessions/sess_abc123" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "session_id": "sess_abc123",
  "messages": [
    {
      "role": "user",
      "content": "什么是 RAG 技术？",
      "created_at": "2024-01-15T10:00:00"
    },
    {
      "role": "assistant",
      "content": "RAG（检索增强生成）是一种...",
      "model": "deepseek-chat",
      "tokens_used": 256,
      "created_at": "2024-01-15T10:00:05"
    }
  ]
}
```

---

### 6. 删除会话

**端点**：`DELETE /v1/history/sessions/{session_id}`

**功能**：删除指定会话及其所有历史消息

#### 请求示例

```bash
curl -X DELETE "http://localhost:8000/v1/history/sessions/sess_abc123" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "success": true,
  "message": "Session deleted"
}
```

---

### 7. 下载文档

**端点**：`GET /v1/download/{doc_id}`

**功能**：下载指定文档的原始文件

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档ID |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/v1/download/doc_abc123" \
  -H "Authorization: Bearer <token>" \
  -O  # 保存到文件
```

#### 响应

返回文件内容，Content-Type 根据文件类型自动设置。

---

## Admin 服务 API

Base URL: `http://localhost:8001`

### 1. 获取文档列表

**端点**：`GET /api/documents`

**功能**：分页获取所有文档列表

#### 查询参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| size | integer | 否 | 每页数量，默认 10，最大 100 |
| keyword | string | 否 | 搜索关键词（标题模糊匹配） |
| status | integer | 否 | 状态筛选：0-未解析，1-解析中，2-失败，3-完成 |

#### 请求示例

```bash
curl -X GET "http://localhost:8001/api/documents?page=1&size=10&status=3" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "total": 100,
  "page": 1,
  "size": 10,
  "items": [
    {
      "id": "doc_abc123",
      "file_name": "技术文档.pdf",
      "file_size": 1024576,
      "file_ext": "pdf",
      "title": "技术文档",
      "description": "产品技术说明文档",
      "parse_status": 3,
      "parse_message": "解析完成",
      "chunk_count": 25,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:05:00"
    }
  ]
}
```

#### 解析状态说明

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 0 | 未解析 | 文件已上传，等待处理 |
| 1 | 解析中 | Worker 正在处理 |
| 2 | 失败 | 解析出错，查看 parse_message |
| 3 | 完成 | 解析成功，已建立索引 |

---

### 2. 上传文档

**端点**：`POST /api/documents`

**功能**：上传新文档并创建解析任务

#### 请求参数（multipart/form-data）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 上传的文件（支持 pdf, docx, txt, md 等） |
| title | string | 否 | 文档标题，默认使用文件名 |
| description | string | 否 | 文档描述 |
| parse_immediately | boolean | 否 | 是否立即解析，默认 `true` |

#### 请求示例

```bash
curl -X POST http://localhost:8001/api/documents \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/document.pdf" \
  -F "title=技术白皮书" \
  -F "description=2024年技术架构白皮书" \
  -F "parse_immediately=true"
```

#### 响应示例

```json
{
  "id": "doc_def456",
  "file_name": "document.pdf",
  "file_size": 2048576,
  "title": "技术白皮书",
  "description": "2024年技术架构白皮书",
  "parse_status": 1,
  "parse_message": "等待解析",
  "created_at": "2024-01-15T11:00:00"
}
```

#### 支持的文件格式

| 扩展名 | MIME 类型 | 说明 |
|--------|-----------|------|
| .pdf | application/pdf | PDF 文档 |
| .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | Word 文档 |
| .doc | application/msword | Word 文档（旧格式） |
| .txt | text/plain | 纯文本 |
| .md | text/markdown | Markdown 文档 |
| .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | Excel 表格 |
| .xls | application/vnd.ms-excel | Excel 表格（旧格式） |
| .pptx | application/vnd.openxmlformats-officedocument.presentationml.presentation | PPT 演示 |
| .ppt | application/vnd.ms-powerpoint | PPT 演示（旧格式） |

---

### 3. 删除文档

**端点**：`DELETE /api/documents/{doc_id}`

**功能**：删除文档及其所有相关数据（文件、索引、任务记录）

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档ID |

#### 请求示例

```bash
curl -X DELETE "http://localhost:8001/api/documents/doc_abc123" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "success": true,
  "message": "Document deleted"
}
```

---

### 4. 更新文档信息

**端点**：`PUT /api/documents/{doc_id}`

**功能**：更新文档的标题和描述

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档ID |

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 新标题 |
| description | string | 否 | 新描述 |

#### 请求示例

```bash
curl -X PUT "http://localhost:8001/api/documents/doc_abc123" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "新标题",
    "description": "更新后的描述"
  }'
```

#### 响应示例

```json
{
  "id": "doc_abc123",
  "title": "新标题",
  "description": "更新后的描述",
  "updated_at": "2024-01-15T12:00:00"
}
```

---

### 5. 创建解析任务

**端点**：`POST /api/documents/{doc_id}/parse`

**功能**：为已上传但未解析的文档手动创建解析任务

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档ID |

#### 请求示例

```bash
curl -X POST "http://localhost:8001/api/documents/doc_abc123/parse" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例

```json
{
  "task_id": "task_xyz789",
  "doc_id": "doc_abc123",
  "status": 1,
  "message": "解析任务已创建"
}
```

---

### 6. 获取文档状态

**端点**：`GET /api/documents/{doc_id}/status`

**功能**：查询文档的解析状态和进度

#### 路径参数

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档ID |

#### 请求示例

```bash
curl -X GET "http://localhost:8001/api/documents/doc_abc123/status" \
  -H "Authorization: Bearer <token>"
```

#### 响应示例（解析中）

```json
{
  "doc_id": "doc_abc123",
  "status": 1,
  "message": "正在解析...",
  "progress": 45,
  "started_at": "2024-01-15T10:00:00"
}
```

#### 响应示例（已完成）

```json
{
  "doc_id": "doc_abc123",
  "status": 3,
  "message": "解析完成",
  "chunk_count": 25,
  "completed_at": "2024-01-15T10:05:00"
}
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 Token 过期 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 422 | Validation Error | 参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| `Not authenticated` | 缺少 Token 或 Token 无效 | 检查 Authorization 头 |
| `Token has expired` | Token 已过期 | 重新登录获取新 Token |
| `Invalid file format` | 不支持的文件格式 | 检查文件扩展名 |
| `File too large` | 文件超过大小限制（默认 50MB） | 压缩文件或分卷上传 |
| `Document not found` | 文档ID 不存在 | 检查 doc_id 是否正确 |
| `Session not found` | 会话ID 不存在 | 检查 session_id 是否正确 |

---

## 限流说明

### 限流策略

为了保护系统资源，API 实施以下限流策略：

| 接口类型 | 限流规则 | 说明 |
|----------|----------|------|
| 问答接口 | 60 次/分钟/用户 | 防止滥用 |
| 文档上传 | 10 次/分钟/用户 | 防止存储爆满 |
| 登录接口 | 5 次/分钟/IP | 防止暴力破解 |

### 限流响应

当触发限流时，返回 429 Too Many Requests：

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 30
}
```

---

## SDK 使用示例

### Python

```python
import requests

class RAGFlowClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def login(self, username: str, password: str):
        """登录并保存 Token"""
        resp = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        self.headers["Authorization"] = f"Bearer {self.token}"
        return resp.json()
    
    def chat(self, question: str, session_id: str = None):
        """发送问答请求（非流式）"""
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json={
                "messages": [{"role": "user", "content": question}],
                "stream": False,
                "session_id": session_id
            }
        )
        resp.raise_for_status()
        return resp.json()
    
    def chat_stream(self, question: str, session_id: str = None):
        """发送问答请求（流式）"""
        import json
        
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json={
                "messages": [{"role": "user", "content": question}],
                "stream": True,
                "session_id": session_id
            },
            stream=True
        )
        
        for line in resp.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    yield json.loads(data)
    
    def upload_document(self, file_path: str, title: str = None):
        """上传文档"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'title': title} if title else {}
            resp = requests.post(
                f"{self.base_url}/api/documents",
                headers={"Authorization": self.headers["Authorization"]},
                files=files,
                data=data
            )
        resp.raise_for_status()
        return resp.json()


# 使用示例
client = RAGFlowClient("http://localhost:8000")
client.login("testuser", "password123")

# 流式对话
for chunk in client.chat_stream("什么是 RAG？"):
    print(chunk["choices"][0]["delta"].get("content", ""), end="")
```

### JavaScript/TypeScript

```typescript
class RAGFlowClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
  }

  async login(username: string, password: string) {
    const resp = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await resp.json();
    this.token = data.access_token;
    return data;
  }

  async *chatStream(question: string, sessionId?: string) {
    const resp = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: question }],
        stream: true,
        session_id: sessionId
      })
    });

    const reader = resp.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          yield JSON.parse(data);
        }
      }
    }
  }
}

// 使用示例
const client = new RAGFlowClient('http://localhost:8000');
await client.login('testuser', 'password123');

// 流式对话
for await (const chunk of client.chatStream('什么是 RAG？')) {
  console.log(chunk.choices[0].delta.content);
}
```

---

## WebSocket 接口（可选）

如需实时获取文档解析进度，可以使用 WebSocket：

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/documents/doc_abc123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress, '%');
  console.log('Status:', data.status);
};
```

**注意**：WebSocket 接口需要额外配置，默认不启用。
