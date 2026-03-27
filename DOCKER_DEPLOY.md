# Smart RAGFlow Docker 部署指南

## 📁 生成的文件

已为你生成 5 个独立服务的 Dockerfile：

| 服务 | 路径 | 端口 | 技术栈 |
|-----|------|-----|--------|
| backend_admin | `backend_admin/Dockerfile` | 8001 | FastAPI + SQLAlchemy |
| backend_qa | `backend_QA/Dockerfile` | 8000 | FastAPI + LangChain |
| backend_parser | `backend_parser/Dockerfile` | - | Python Worker |
| frontend_admin | `frontend_admin/Dockerfile` | 8080 | Vue3 + Vite |
| frontend_qa | `frontend_QA/Dockerfile` | 8080 | Vue3 + Vite |

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止所有服务
docker-compose down
```

### 方式二：单独构建和运行

```bash
# 1. 构建镜像
cd backend_admin
docker build -t smart-ragflow/backend-admin:latest ..

# 2. 运行容器
docker run -d \
  --name backend-admin \
  -p 8001:8001 \
  --env-file ../.env \
  smart-ragflow/backend-admin:latest

# 其他服务类似...
```

### 方式三：使用构建脚本

```bash
# 构建所有镜像
chmod +x scripts/build-images.sh
./scripts/build-images.sh

# 推送到私有仓库（可选）
REGISTRY=your-registry.com/ PUSH=true ./scripts/build-images.sh
```

## 🔧 镜像优化说明

### Python 后端服务
- **多阶段构建**：分离依赖安装和运行环境
- **slim 基础镜像**：`python:3.11-slim` 比标准镜像小 ~50%
- **虚拟环境**：隔离依赖，避免冲突
- **非 root 用户**：使用 `appuser` 运行，提高安全性

### 前端服务
- **多阶段构建**：Node 构建 + Nginx 服务
- **alpine 基础镜像**：`nginx:alpine` 体积极小
- **非 root 用户**：使用 `nginx` 用户运行
- **非特权端口**：使用 8080 而非 80

## 📊 镜像大小预估

| 服务 | 预估大小 |
|-----|---------|
| backend_admin | ~180MB |
| backend_qa | ~250MB |
| backend_parser | ~220MB |
| frontend_admin | ~25MB |
| frontend_qa | ~25MB |

## 🔗 服务访问

启动后可通过以下地址访问：

| 服务 | 本地地址 |
|-----|---------|
| QA API | http://localhost:8000 |
| Admin API | http://localhost:8001 |
| QA 前端 | http://localhost:3000 |
| Admin 前端 | http://localhost:3001 |

## ⚙️ 环境变量

确保 `.env` 文件中包含以下配置：

```bash
# 数据库
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# Redis
REDIS_URL=redis://localhost:6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 🛠️ 故障排查

```bash
# 查看容器日志
docker logs smart-ragflow-qa
docker logs smart-ragflow-admin

# 进入容器调试
docker exec -it smart-ragflow-qa sh

# 检查健康状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Health}}"
```

## 📝 注意事项

1. **backend_common 依赖**：所有 Python 服务共享 `backend_common` 模块，Dockerfile 中已正确配置复制路径
2. **构建上下文**：Python 服务需要从项目根目录构建（`docker build -f service/Dockerfile .`）
3. **端口映射**：前端服务在容器内使用 8080 端口，映射到主机的 3000/3001
