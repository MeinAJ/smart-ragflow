# Backend Admin

Smart RAGFlow 文档管理后台服务。

## 功能特性

- 📤 文档上传（支持 MD5 去重和覆盖）
- 📋 文档列表查询（分页、搜索）
- 📝 文档信息更新
- 🗑️ 文档删除
- ▶️ 文档解析（创建待处理任务）

## 5个核心接口

| 序号 | 方法 | 接口 | 描述 |
|------|------|------|------|
| 1 | GET | `/api/documents` | 查询文档列表 |
| 2 | POST | `/api/documents` | 上传/创建文档 |
| 3 | DELETE | `/api/documents/{doc_id}` | 删除文档 |
| 4 | PUT | `/api/documents/{doc_id}` | 更新文档信息 |
| 5 | POST | `/api/documents/{doc_id}/parse` | 创建解析任务 |

## 数据库表结构

### documents（文档表）

```sql
CREATE TABLE documents (
    id VARCHAR(64) PRIMARY KEY COMMENT '主键',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_size BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件MD5',
    file_ext VARCHAR(20) NOT NULL COMMENT '文件后缀',
    file_url VARCHAR(500) NOT NULL COMMENT 'MinIO URL',
    parse_status TINYINT NOT NULL DEFAULT 0 COMMENT '0-未解析,1-正在解析,2-异常,3-完成',
    parse_message TEXT COMMENT '状态消息',
    chunk_count INT DEFAULT 0 COMMENT '分块数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### parse_tasks（解析任务表）

```sql
CREATE TABLE parse_tasks (
    id VARCHAR(64) PRIMARY KEY COMMENT '主键',
    doc_id VARCHAR(64) NOT NULL COMMENT '文档ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_size BIGINT NOT NULL COMMENT '文件大小',
    file_ext VARCHAR(20) NOT NULL COMMENT '文件后缀',
    file_url VARCHAR(500) NOT NULL COMMENT 'MinIO URL',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件MD5',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0-未解析,1-待解析,2-解析中,3-异常,4-完成',
    error_message TEXT COMMENT '错误信息',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

## 快速开始

### 1. 安装依赖

```bash
cd backend-admin
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件配置数据库和 MinIO
```

### 3. 初始化数据库

```bash
# 执行 SQL 创建表
mysql -u root -p ragflow < database/schema.sql
```

### 4. 启动服务

```bash
python main.py
```

服务将运行在 http://localhost:8001

## 架构说明

### 文档上传流程

1. 接收上传的文件
2. 计算文件 MD5
3. 检查是否已存在（MD5 匹配）
   - 存在：删除旧文件和旧任务，更新记录
   - 不存在：创建新记录
4. 上传文件到 MinIO
5. 创建文档记录
6. 如果 `parse_immediately=true`，创建解析任务（状态：待解析）

### 解析任务流程

1. 用户点击"解析"按钮或上传时选择"立即解析"
2. 创建 `parse_tasks` 记录，状态为 `1-待解析`
3. 后台服务（parser）轮询读取待解析任务
4. 后台服务开始处理，更新状态为 `2-解析中`
5. 处理完成后更新状态为 `4-解析完成` 或 `3-解析异常`

## 与 Parser 的关系

- **backend-admin**: Web 服务，提供 HTTP API，管理文档和任务
- **parser**: 后台服务，消费 `parse_tasks` 表中的待处理任务，执行实际的文档解析
