# Smart RAGFlow 贡献指南

> 欢迎贡献代码！本指南将帮助你快速上手开发流程。

## 目录

- [开发环境搭建](#开发环境搭建)
- [项目结构说明](#项目结构说明)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [调试技巧](#调试技巧)

---

## 开发环境搭建

### 1. 克隆项目

```bash
git clone https://github.com/your-org/smart-ragflow.git
cd smart-ragflow
```

### 2. 创建虚拟环境

```bash
# 使用 uv（推荐）
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 使用 venv
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
# 安装项目依赖
uv pip install -e ".[dev]"

# 或使用 pip
pip install -e ".[dev]"
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置本地开发环境
```

### 5. 启动基础设施

使用 Docker Compose 启动依赖服务：

```bash
docker-compose -f docker/docker-compose.dev.yml up -d mysql opensearch redis minio
```

### 6. 初始化数据库

```bash
mysql -u root -p -e "CREATE DATABASE ragflow CHARACTER SET utf8mb4;"
mysql -u root -p ragflow < scripts/create_chat_history_table.sql
```

### 7. 启动开发服务器

```bash
# 方式一：使用一键启动脚本
python start_all.py --services backend

# 方式二：分别启动
# 终端 1: Admin 服务
uvicorn backend_admin.main:app --reload --port 8001

# 终端 2: QA 服务
uvicorn backend_QA.main:app --reload --port 8000

# 终端 3: Worker
python backend_parser/worker.py
```

### 8. 验证安装

```bash
# 检查 API 文档
curl http://localhost:8000/docs
curl http://localhost:8001/docs
```

---

## 项目结构说明

```
smart-ragflow/
├── backend_QA/              # 问答服务
│   ├── api/                 # API 路由
│   │   ├── chat.py         # 问答接口
│   │   ├── auth.py         # 认证接口
│   │   └── history.py      # 历史记录接口
│   ├── core/               # RAG 核心流程
│   │   ├── graph.py        # LangGraph 定义
│   │   ├── nodes.py        # 节点实现
│   │   └── state.py        # 状态定义
│   ├── services/           # 业务服务
│   │   ├── llm.py          # LLM 客户端
│   │   ├── opensearch.py   # 检索服务
│   │   └── mmr.py          # 重排序算法
│   └── main.py             # 服务入口
│
├── backend_admin/          # 文档管理服务
│   ├── api/
│   │   └── documents.py    # 文档 CRUD
│   ├── models/             # SQLAlchemy 模型
│   └── services/           # 业务逻辑
│
├── backend_parser/         # 文档解析服务
│   ├── worker.py           # Worker 主程序
│   ├── deepdoc_parser.py   # 文档解析器
│   ├── chunker.py          # 文本分块
│   └── embedding.py        # 向量化服务
│
├── backend_common/         # 公共模块
│   ├── clients/            # 客户端封装
│   ├── config.py           # 全局配置
│   └── models.py           # 共享模型
│
├── frontend_QA/            # 问答前端（Vue3）
│   └── src/
│       ├── views/          # 页面组件
│       └── components/     # 可复用组件
│
├── frontend_admin/         # 管理后台前端
│   └── src/
│       └── views/          # 页面组件
│
├── docs/                   # 文档
├── scripts/                # 脚本工具
├── tests/                  # 测试用例
└── docker/                 # Docker 配置
```

### 模块职责

| 模块 | 职责 | 关键文件 |
|------|------|----------|
| backend_QA | 处理用户问答，执行 RAG 流程 | `core/graph.py`, `api/chat.py` |
| backend_admin | 管理文档、用户、系统配置 | `api/documents.py` |
| backend_parser | 后台异步处理文档解析 | `worker.py`, `deepdoc_parser.py` |
| backend_common | 提供共享的客户端、配置、模型 | `config.py`, `clients/` |

---

## 代码规范

### Python 代码规范

遵循 PEP 8 规范，使用以下工具检查：

```bash
# 代码格式化
black backend_*

# 导入排序
isort backend_*

# 类型检查
mypy backend_QA backend_admin backend_parser backend_common

# 代码检查
flake8 backend_* --max-line-length=100
```

### 代码风格

#### 1. 函数文档字符串

```python
async def retrieve_documents(
    query: str,
    vector: List[float],
    top_k: int = 10
) -> List[Document]:
    """
    检索相关文档。

    执行混合检索（BM25 + 向量），返回最相关的文档列表。

    Args:
        query: 搜索查询文本
        vector: 查询向量
        top_k: 返回文档数量

    Returns:
        相关文档列表，按相关性排序

    Raises:
        SearchError: 检索服务异常时抛出

    Example:
        >>> docs = await retrieve_documents("RAG技术", [0.1, 0.2, ...], 5)
        >>> len(docs)
        5
    """
```

#### 2. 类型注解

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    """聊天请求模型。"""
    messages: List[ChatMessage]
    stream: bool = True
    session_id: Optional[str] = None

async def process_chat(
    request: ChatRequest,
    user_id: int
) -> AsyncIterator[str]:
    ...
```

#### 3. 错误处理

```python
try:
    result = await some_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise ServiceUnavailableError("服务暂时不可用") from e
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise InternalError("内部错误") from e
```

#### 4. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 调试信息
logger.debug(f"Processing request: {request_id}")

# 一般信息
logger.info(f"User {user_id} created session {session_id}")

# 警告
logger.warning(f"Slow query detected: {query_time}s")

# 错误
logger.error(f"Failed to parse document: {doc_id}")

# 异常（包含堆栈）
logger.exception(f"Unexpected error processing {task_id}")
```

### 前端代码规范

```bash
# ESLint 检查
cd frontend_QA && npm run lint
cd frontend_admin && npm run lint

# 自动修复
cd frontend_QA && npm run lint:fix
```

---

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加文档批量上传功能` |
| `fix` | 修复 Bug | `fix: 修复 Embedding 缓存失效问题` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `style` | 代码格式 | `style: 格式化 Python 代码` |
| `refactor` | 重构 | `refactor: 优化检索逻辑` |
| `perf` | 性能优化 | `perf: 减少 Embedding 调用次数` |
| `test` | 测试 | `test: 添加 chat API 测试` |
| `chore` | 杂项 | `chore: 更新依赖版本` |

### 提交示例

```bash
# 功能提交
git commit -m "feat: 添加会话标题自动生成功能

- 使用 LLM 根据首条消息生成会话标题
- 添加标题编辑接口
- 前端显示标题输入框

Closes #123"

# 修复提交
git commit -m "fix: 修复大文件上传超时问题

- 增加上传超时时间到 5 分钟
- 添加进度条显示
- 优化前端上传逻辑

Fixes #456"
```

---

## Pull Request 流程

### 1. 创建分支

```bash
# 从 main 分支创建特性分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 分支命名规范
# feature/*  - 新功能
# fix/*      - Bug 修复
# docs/*     - 文档更新
# refactor/* - 代码重构
```

### 2. 开发调试

```bash
# 开发过程中频繁提交
git add .
git commit -m "feat: 实现文档搜索功能"

# 保持与主分支同步
git fetch origin
git rebase origin/main
```

### 3. 测试

```bash
# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 检查测试覆盖率
pytest --cov=backend_QA --cov-report=html
```

### 4. 提交 PR

```bash
# 推送到远程
git push origin feature/your-feature-name

# 然后在 GitHub 上创建 PR
```

### PR 描述模板

```markdown
## 描述
简要描述这个 PR 做了什么。

## 变更内容
- [x] 功能 A 实现
- [x] 功能 B 优化
- [ ] 功能 C 待完成

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试验证

## 相关 Issue
Closes #123

## 截图（如适用）
![screenshot](url)
```

### 5. 代码审查

- 确保 CI 检查通过
- 至少 1 个审查者批准
- 解决所有审查意见
- 保持 PR 小而专注

---

## 调试技巧

### 1. 后端调试

#### 使用 PDB

```python
# 在代码中插入断点
import pdb; pdb.set_trace()

# 常用命令
# n - 下一行
# s - 进入函数
# c - 继续执行
# p variable - 打印变量
# l - 显示代码
```

#### 使用 VSCode 调试

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: QA API",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["backend_QA.main:app", "--reload", "--port", "8000"],
            "jinja": true
        },
        {
            "name": "Python: Worker",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend_parser/worker.py",
            "console": "integratedTerminal"
        }
    ]
}
```

#### 日志调试

```bash
# 实时查看日志
tail -f logs/qa_api.log | grep ERROR

# 按请求 ID 过滤
 tail -f logs/qa_api.log | grep "req_abc123"
```

### 2. 前端调试

```bash
# Chrome DevTools
# - Network: 查看 API 请求
# - Console: 查看日志
# - Vue DevTools: Vue 组件调试

# 在代码中添加 debugger
debugger;
```

### 3. 数据库调试

```bash
# MySQL 慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

# 查看当前查询
SHOW PROCESSLIST;

# Redis 监控
redis-cli monitor

# OpenSearch 慢查询
curl "localhost:9200/_cat/thread_pool/search?v"
```

### 4. 性能分析

```python
# Python 性能分析
from cProfile import Profile
from pstats import Stats

profiler = Profile()
profiler.enable()

# 你的代码
result = await process_documents()

profiler.disable()
stats = Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

---

## 测试指南

### 单元测试

```python
# tests/unit/test_mmr.py
import pytest
from backend_QA.services.mmr import mmr_rerank

def test_mmr_rerank_basic():
    """测试 MMR 基础功能。"""
    query_vector = [1.0, 0.0, 0.0]
    documents = [
        {"id": "doc1", "vector": [0.9, 0.1, 0.0]},
        {"id": "doc2", "vector": [0.8, 0.2, 0.0]},
        {"id": "doc3", "vector": [0.1, 0.9, 0.0]},
    ]
    
    result = mmr_rerank(query_vector, documents, lambda_param=0.5, top_k=2)
    
    assert len(result) == 2
    assert result[0]["id"] == "doc1"  # 最相关
```

### 集成测试

```python
# tests/integration/test_chat_api.py
import pytest
from httpx import AsyncClient
from backend_QA.main import app

@pytest.mark.asyncio
async def test_chat_completions():
    """测试问答接口。"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test_token"},
            json={
                "messages": [{"role": "user", "content": "测试"}],
                "stream": False
            }
        )
        assert response.status_code == 200
```

### 运行测试

```bash
# 全部测试
pytest

# 指定模块
pytest tests/unit/services/

# 指定测试
pytest tests/unit/test_mmr.py::test_mmr_rerank_basic

# 带覆盖率
pytest --cov=backend_QA --cov-report=term-missing

# 并行测试
pytest -n auto
```

---

## 常见问题

### Q: 修改代码后没有生效？

A: 确保：
1. 使用了 `--reload` 参数
2. 不是语法错误导致服务重启失败
3. 清除了 Python 缓存：`find . -type d -name __pycache__ -exec rm -r {} +`

### Q: 数据库连接失败？

A: 检查：
1. MySQL 服务是否运行：`sudo systemctl status mysql`
2. 用户名密码是否正确
3. 数据库是否存在

### Q: 前端无法连接后端？

A: 检查：
1. CORS 配置是否包含前端地址
2. 后端服务是否正常运行
3. 端口是否冲突

### Q: Worker 不处理任务？

A: 检查：
1. Worker 进程是否在运行
2. 数据库中是否有 WAITING 状态的任务
3. Worker 日志是否有错误

---

## 联系方式

- **Issue**: [GitHub Issues](https://github.com/your-org/smart-ragflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/smart-ragflow/discussions)
- **Email**: dev@your-org.com

---

感谢你的贡献！🎉
