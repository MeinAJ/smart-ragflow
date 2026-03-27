#!/bin/bash
# 构建所有服务的 Docker 镜像

set -e

REGISTRY="${REGISTRY:-}"
# TAG 默认为当前时间戳，格式：20240327-180135
TAG="${TAG:-$(date +%Y%m%d-%H%M%S)}"
PROJECT_NAME="smart-ragflow"

echo "🐳 构建 Smart RAGFlow Docker 镜像..."
echo "================================"

# 后端服务
echo ""
echo "📦 构建 backend_admin..."
docker build -f backend_admin/Dockerfile -t "${REGISTRY}${PROJECT_NAME}/backend-admin:${TAG}" .

echo ""
echo "📦 构建 backend_qa..."
docker build -f backend_QA/Dockerfile -t "${REGISTRY}${PROJECT_NAME}/backend-qa:${TAG}" .

echo ""
echo "📦 构建 backend_parser..."
docker build -f backend_parser/Dockerfile -t "${REGISTRY}${PROJECT_NAME}/backend-parser:${TAG}" .

# 前端服务
echo ""
echo "📦 构建 frontend_admin..."
docker build -f frontend_admin/Dockerfile -t "${REGISTRY}${PROJECT_NAME}/frontend-admin:${TAG}" ./frontend_admin

echo ""
echo "📦 构建 frontend_qa..."
docker build -f frontend_QA/Dockerfile -t "${REGISTRY}${PROJECT_NAME}/frontend-qa:${TAG}" ./frontend_QA

echo ""
echo "================================"
echo "✅ 所有镜像构建完成！"
echo ""
echo "镜像列表："
docker images "${PROJECT_NAME}/*:${TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# 可选：推送到仓库
if [ -n "$REGISTRY" ] && [ "$PUSH" = "true" ]; then
    echo ""
    echo "📤 推送到镜像仓库..."
    docker push "${REGISTRY}${PROJECT_NAME}/backend-admin:${TAG}"
    docker push "${REGISTRY}${PROJECT_NAME}/backend-qa:${TAG}"
    docker push "${REGISTRY}${PROJECT_NAME}/backend-parser:${TAG}"
    docker push "${REGISTRY}${PROJECT_NAME}/frontend-admin:${TAG}"
    docker push "${REGISTRY}${PROJECT_NAME}/frontend-qa:${TAG}"
    echo "✅ 推送完成！"
fi
