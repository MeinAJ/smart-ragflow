# Backend Parser

文档解析服务模块。

## 目录结构

```
backend_parser/
├── __init__.py              # 包初始化
├── cli.py                   # 命令行入口
├── worker.py                # 后台解析工作进程
├── config.py                # 解析服务配置
├── chunker.py               # 文档分块
├── tokenizer.py             # Token 计数
├── deepdoc_parser.py        # DeepDoc 解析器
├── models.py                # 数据模型
│
├── core/                    # 核心功能
│   ├── __init__.py
│   └── ...
│
├── models/                  # 数据模型（导入导出）
│   └── __init__.py
│
├── services/                # 服务层
│   ├── __init__.py
│   └── ...
│
└── utils/                   # 工具函数
    ├── __init__.py
    └── ...
```

## 使用方式

### 1. 后台 Worker 模式（推荐）

```bash
python backend_parser/worker.py
```

Worker 会：
1. 轮询数据库 `parse_tasks` 表
2. 获取状态为 `待解析` 的任务
3. 执行文档解析
4. 更新任务状态

### 2. 命令行模式

```bash
python backend_parser/cli.py --help
```

### 3. 编程调用

```python
from backend_parser.services import DocumentParseService

async with DocumentParseService() as service:
    result = await service.process(
        file_url="http://minio/bucket/file.pdf",
        doc_id="doc-xxx"
    )
```

## 数据流

```
backend_admin (上传文档)
    ↓
parse_tasks (创建任务，status=待解析)
    ↓
backend_parser/worker.py (轮询获取任务)
    ↓
DocumentParseService.process() (执行解析)
    ↓
OpenSearch (存储向量)
    ↓
parse_tasks (更新状态为完成)
```
