# Smart RAGFlow 部署指南

> 生产环境部署、配置优化和运维监控的完整指南。

## 目录

- [环境要求](#环境要求)
- [Docker 部署（推荐）](#docker-部署推荐)
- [手动部署](#手动部署)
- [配置优化](#配置优化)
- [监控与日志](#监控与日志)
- [备份与恢复](#备份与恢复)
- [故障排查](#故障排查)

---

## 环境要求

### 最低配置（开发/测试）

| 组件 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| 全服务 | 4 核 | 8 GB | 50 GB | 单机部署 |
| MySQL | 1 核 | 1 GB | 10 GB | 可复用现有实例 |
| OpenSearch | 2 核 | 4 GB | 20 GB | 向量检索需要内存 |
| Redis | 0.5 核 | 512 MB | 1 GB | 可复用现有实例 |
| MinIO | 1 核 | 1 GB | 20 GB | 文件存储 |

### 推荐配置（生产环境）

| 组件 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| Backend QA | 4 核 | 4 GB | 10 GB | 2+ 实例负载均衡 |
| Backend Admin | 2 核 | 2 GB | 10 GB | 2 实例 |
| Parser Worker | 4 核 | 8 GB | 20 GB | 可按需扩容 |
| MySQL | 4 核 | 8 GB | 100 GB | 主从复制 |
| OpenSearch | 8 核 | 32 GB | 500 GB | 3 节点集群 |
| Redis | 2 核 | 4 GB | 10 GB | 主从 + Sentinel |
| MinIO | 4 核 | 8 GB | 1 TB+ | 分布式部署 |
| Nginx | 2 核 | 2 GB | 10 GB | 反向代理 + 负载均衡 |

---

## Docker 部署（推荐）

### 1. 准备环境

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2. 创建部署目录

```bash
mkdir -p /opt/smart-ragflow
cd /opt/smart-ragflow

# 创建必要目录
mkdir -p data/mysql
mkdir -p data/opensearch
mkdir -p data/redis
mkdir -p data/minio
mkdir -p logs
```

### 3. 创建 Docker Compose 文件

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MySQL 数据库
  mysql:
    image: mysql:8.0
    container_name: ragflow-mysql
    environment:
      MYSQL_ROOT_PASSWORD: your_secure_password
      MYSQL_DATABASE: ragflow
      MYSQL_USER: ragflow
      MYSQL_PASSWORD: ragflow_password
    volumes:
      - ./data/mysql:/var/lib/mysql
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10

  # OpenSearch
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    container_name: ragflow-opensearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - ./data/opensearch:/usr/share/opensearch/data
    ports:
      - "9200:9200"
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    container_name: ragflow-redis
    command: redis-server --appendonly yes
    volumes:
      - ./data/redis:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  # MinIO
  minio:
    image: minio/minio:latest
    container_name: ragflow-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio_secure_password
    volumes:
      - ./data/minio:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    restart: unless-stopped

  # Backend QA
  backend-qa:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: ragflow-qa
    environment:
      - DATABASE_URL=mysql+pymysql://ragflow:ragflow_password@mysql:3306/ragflow?charset=utf8mb4
      - OPENSEARCH_HOST=opensearch
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
    ports:
      - "8000:8000"
    depends_on:
      mysql:
        condition: service_healthy
      opensearch:
        condition: service_started
      redis:
        condition: service_started
    restart: unless-stopped

  # Backend Admin
  backend-admin:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: ragflow-admin
    environment:
      - DATABASE_URL=mysql+pymysql://ragflow:ragflow_password@mysql:3306/ragflow?charset=utf8mb4
      - MINIO_ENDPOINT=minio:9000
    ports:
      - "8001:8001"
    depends_on:
      mysql:
        condition: service_healthy
      minio:
        condition: service_started
    restart: unless-stopped

  # Parser Worker
  parser-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: ragflow-worker
    command: python backend_parser/worker.py
    environment:
      - DATABASE_URL=mysql+pymysql://ragflow:ragflow_password@mysql:3306/ragflow?charset=utf8mb4
      - OPENSEARCH_HOST=opensearch
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - EMBEDDING_URL=${EMBEDDING_URL}
    depends_on:
      mysql:
        condition: service_healthy
      opensearch:
        condition: service_started
      minio:
        condition: service_started
    restart: unless-stopped

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: ragflow-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/ssl:/etc/nginx/ssl
      - ./frontend_QA/dist:/usr/share/nginx/html/qa
      - ./frontend_admin/dist:/usr/share/nginx/html/admin
    depends_on:
      - backend-qa
      - backend-admin
    restart: unless-stopped

networks:
  default:
    name: ragflow-network
```

### 4. 创建 Dockerfile

```dockerfile
# docker/Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml .
COPY backend_QA ./backend_QA
COPY backend_admin ./backend_admin
COPY backend_parser ./backend_parser
COPY backend_common ./backend_common

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 暴露端口
EXPOSE 8000 8001

# 默认启动命令（会被 docker-compose 覆盖）
CMD ["uvicorn", "backend_QA.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5. 创建 Nginx 配置

```nginx
# docker/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream qa_backend {
        server backend-qa:8000;
    }

    upstream admin_backend {
        server backend-admin:8001;
    }

    # QA API
    server {
        listen 80;
        server_name qa-api.yourdomain.com;

        location / {
            proxy_pass http://qa_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            # SSE 支持
            proxy_http_version 1.1;
            proxy_set_header Connection '';
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 86400s;
        }
    }

    # Admin API
    server {
        listen 80;
        server_name admin-api.yourdomain.com;

        location / {
            proxy_pass http://admin_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # Frontend QA
    server {
        listen 80;
        server_name qa.yourdomain.com;
        root /usr/share/nginx/html/qa;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }
    }

    # Frontend Admin
    server {
        listen 80;
        server_name admin.yourdomain.com;
        root /usr/share/nginx/html/admin;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

### 6. 环境变量配置

```bash
# .env.production
# OpenAI API 配置
OPENAI_API_KEY=sk-your-secure-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# Embedding 服务配置
EMBEDDING_URL=http://your-embedding-service:8080/embed
EMBEDDING_MODEL=bge-m3

# JWT 密钥（生产环境必须修改）
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
```

### 7. 启动服务

```bash
# 加载环境变量
export $(cat .env.production | xargs)

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f backend-qa
docker-compose logs -f parser-worker
```

### 8. 初始化数据库

```bash
# 执行数据库初始化脚本
docker-compose exec mysql mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS ragflow CHARACTER SET utf8mb4;
"

# 创建表结构（SQL 文件已挂载到容器）
docker-compose exec mysql mysql -u ragflow -p ragflow < scripts/create_chat_history_table.sql
```

---

## 手动部署

### 1. 准备服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装 Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 MySQL
sudo apt install -y mysql-server-8.0

# 安装 Redis
sudo apt install -y redis-server

# 安装 MinIO（二进制方式）
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# 安装 OpenSearch（参考官方文档）
```

### 2. 配置 MySQL

```bash
# 登录 MySQL
sudo mysql -u root

# 创建数据库和用户
CREATE DATABASE ragflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ragflow'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ragflow.* TO 'ragflow'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 执行初始化脚本
mysql -u ragflow -p ragflow < scripts/create_chat_history_table.sql
```

### 3. 配置系统服务

#### Backend QA 服务

```ini
# /etc/systemd/system/ragflow-qa.service
[Unit]
Description=Smart RAGFlow QA Service
After=network.target mysql.service redis.service

[Service]
Type=simple
User=ragflow
WorkingDirectory=/opt/smart-ragflow
Environment=PYTHONPATH=/opt/smart-ragflow
EnvironmentFile=/opt/smart-ragflow/.env
ExecStart=/opt/smart-ragflow/.venv/bin/uvicorn backend_QA.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Parser Worker 服务

```ini
# /etc/systemd/system/ragflow-worker.service
[Unit]
Description=Smart RAGFlow Parser Worker
After=network.target mysql.service

[Service]
Type=simple
User=ragflow
WorkingDirectory=/opt/smart-ragflow
Environment=PYTHONPATH=/opt/smart-ragflow
EnvironmentFile=/opt/smart-ragflow/.env
ExecStart=/opt/smart-ragflow/.venv/bin/python backend_parser/worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4. 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable ragflow-qa
sudo systemctl enable ragflow-worker
sudo systemctl start ragflow-qa
sudo systemctl start ragflow-worker

# 查看状态
sudo systemctl status ragflow-qa
sudo systemctl status ragflow-worker

# 查看日志
sudo journalctl -u ragflow-qa -f
```

---

## 配置优化

### 1. MySQL 优化

```ini
# /etc/mysql/mysql.conf.d/mysqld.cnf
[mysqld]
# 基础配置
innodb_buffer_pool_size = 2G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# 连接配置
max_connections = 200
wait_timeout = 600
interactive_timeout = 600

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### 2. OpenSearch 优化

```yaml
# opensearch.yml
# JVM 配置（jvm.options）
-Xms8g
-Xmx8g

# 集群配置
cluster.name: ragflow-cluster
node.name: node-1
cluster.initial_master_nodes: ["node-1"]

# 索引配置
indices.memory.index_buffer_size: 20%
indices.query.bool.max_clause_count: 8192
```

### 3. Nginx 优化

```nginx
# nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 65535;
    use epoll;
    multi_accept on;
}

http {
    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    
    # 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;
    
    # 连接池
    upstream backend {
        server 127.0.0.1:8000 weight=5;
        server 127.0.0.1:8002 weight=5;
        keepalive 32;
    }
}
```

---

## 监控与日志

### 1. 日志配置

```python
# logging.conf
[loggers]
keys=root,qa,worker

[handlers]
keys=console,file

[formatters]
keys=standard

[logger_root]
level=INFO
handlers=console,file

[logger_qa]
level=INFO
handlers=file
qualname=backend_QA
propagate=0

[handler_file]
class=handlers.RotatingFileHandler
args=('/var/log/ragflow/app.log', 'a', 104857600, 10)
formatter=standard

[formatter_standard]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
```

### 2. 健康检查端点

```bash
# QA 服务健康检查
curl http://localhost:8000/health

# Admin 服务健康检查
curl http://localhost:8001/health
```

### 3. 监控指标（Prometheus）

```python
# 在 FastAPI 中添加 Prometheus 中间件
from prometheus_client import Counter, Histogram, generate_latest

# 定义指标
request_count = Counter('ragflow_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('ragflow_request_duration_seconds', 'Request duration', ['endpoint'])
```

---

## 备份与恢复

### 1. 数据库备份

```bash
# 自动备份脚本
#!/bin/bash
BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)

# MySQL 备份
mysqldump -u root -p ragflow > $BACKUP_DIR/ragflow_$DATE.sql

# 保留最近 7 天备份
find $BACKUP_DIR -name "ragflow_*.sql" -mtime +7 -delete
```

### 2. OpenSearch 备份

```bash
# 创建快照仓库
curl -X PUT "localhost:9200/_snapshot/ragflow_backup" -H 'Content-Type: application/json' -d'{
  "type": "fs",
  "settings": {
    "location": "/backup/opensearch"
  }
}'

# 创建快照
curl -X PUT "localhost:9200/_snapshot/ragflow_backup/snapshot_$(date +%Y%m%d)"
```

### 3. MinIO 备份

```bash
# 使用 mc 客户端备份
mc mirror local/smart-ragflow backup/minio
```

---

## 故障排查

### 常见问题

#### 1. 服务启动失败

```bash
# 检查端口占用
sudo lsof -i :8000
sudo lsof -i :8001

# 检查配置文件
python -c "from backend_common.config import settings; print(settings)"
```

#### 2. 数据库连接失败

```bash
# 测试数据库连接
mysql -u ragflow -p -h localhost -e "SELECT 1"

# 检查连接数
mysql -u root -p -e "SHOW PROCESSLIST"
```

#### 3. OpenSearch 性能问题

```bash
# 检查集群健康
curl http://localhost:9200/_cluster/health

# 检查索引状态
curl http://localhost:9200/_cat/indices?v

# 检查慢查询
curl http://localhost:9200/_cat/thread_pool/search?v
```

#### 4. 内存不足

```bash
# 查看内存使用
free -h
cat /proc/meminfo

# 查看进程内存
ps aux --sort=-%mem | head -20
```

### 调试技巧

```bash
# 开启详细日志
export LOG_LEVEL=DEBUG

# 性能分析
python -m cProfile -o profile.stats backend_QA/main.py

# 数据库查询分析
SET GLOBAL general_log = 'ON';
SET GLOBAL log_output = 'TABLE';
SELECT * FROM mysql.general_log WHERE argument LIKE '%ragflow%';
```

---

## 升级指南

### 版本升级步骤

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取新版本
git pull origin main

# 3. 更新依赖
pip install -r requirements.txt --upgrade

# 4. 执行数据库迁移
python scripts/migrate.py

# 5. 重启服务
sudo systemctl restart ragflow-qa
sudo systemctl restart ragflow-worker
```

---

## 安全建议

1. **修改默认密码**：所有服务的默认密码必须修改
2. **启用 HTTPS**：使用 SSL/TLS 证书加密通信
3. **防火墙配置**：只开放必要的端口
4. **JWT 密钥**：使用强随机字符串作为 JWT 密钥
5. **定期更新**：及时更新依赖库以修复安全漏洞
6. **访问日志**：记录所有 API 访问日志用于审计

```bash
# 生成强随机 JWT 密钥
openssl rand -hex 32
```
