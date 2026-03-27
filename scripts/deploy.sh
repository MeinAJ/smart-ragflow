#!/bin/bash
# Smart RAGFlow 部署脚本 (兼容 macOS Bash 3.x)
# 流程: 停止容器 -> 删除旧镜像 -> 构建新镜像 -> 启动服务

set -e

# ==================== 配置 ====================
REGISTRY="${REGISTRY:-}"
TAG="${TAG:-$(date +%Y%m%d-%H%M%S)}"
PROJECT_NAME="smart-ragflow"
ENV_FILE="${ENV_FILE:-.env.docker}"

# 颜色
G='\033[0;32m'
Y='\033[1;33m'
R='\033[0;31m'
NC='\033[0m'

log() { echo -e "${G}[DEPLOY]${NC} $1"; }
warn() { echo -e "${Y}[WARN]${NC} $1"; }
err() { echo -e "${R}[ERROR]${NC} $1"; }

# ==================== 服务定义 ====================
# 使用多个平行数组（兼容 Bash 3.x）

SERVICE_NAMES=("backend-parser" "backend-qa" "backend-admin" "frontend-qa" "frontend-admin")
SERVICE_DOCKERFILES=("backend_parser/Dockerfile" "backend_QA/Dockerfile" "backend_admin/Dockerfile" "frontend_QA/Dockerfile" "frontend_admin/Dockerfile")
SERVICE_CONTEXTS=("." "." "." "frontend_QA" "frontend_admin")
SERVICE_PORTS=("" "8000:8000" "8001:8001" "3000:8080" "3001:8080")

# ==================== 辅助函数 ====================

# 根据服务名获取索引
get_service_index() {
    local name=$1
    local i
    for i in "${!SERVICE_NAMES[@]}"; do
        if [ "${SERVICE_NAMES[$i]}" = "$name" ]; then
            echo $i
            return
        fi
    done
    echo "-1"
}

# ==================== 第1步：停止容器 ====================
stop_containers() {
    log "步骤 1/4: 停止容器"
    echo "----------------------------------------"
    
    for name in "${SERVICE_NAMES[@]}"; do
        container="${PROJECT_NAME}-${name}"
        
        if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            warn "停止容器: $container"
            docker stop "$container" >/dev/null 2>&1 || true
            docker rm "$container" >/dev/null 2>&1 || true
        else
            log "容器不存在: $container"
        fi
    done
    echo ""
}

# ==================== 第2步：删除旧镜像 ====================
remove_old_images() {
    log "步骤 2/4: 删除旧镜像"
    echo "----------------------------------------"
    
    for name in "${SERVICE_NAMES[@]}"; do
        image_name="${REGISTRY}${PROJECT_NAME}/${name}"
        
        # 获取该服务的所有镜像（除了即将构建的新标签）
        images=$(docker images "$image_name" --format "{{.Repository}}:{{.Tag}}" | grep -v "$TAG" || true)
        
        if [ -n "$images" ]; then
            echo "$images" | while read -r img; do
                warn "删除镜像: $img"
                docker rmi "$img" >/dev/null 2>&1 || true
            done
        else
            log "无旧镜像: $image_name"
        fi
    done
    
    # 清理悬空镜像
    docker image prune -f >/dev/null 2>&1 || true
    echo ""
}

# ==================== 第3步：构建新镜像 ====================
build_images() {
    log "步骤 3/4: 构建新镜像 (标签: $TAG)"
    echo "----------------------------------------"
    
    local i
    for i in "${!SERVICE_NAMES[@]}"; do
        name="${SERVICE_NAMES[$i]}"
        dockerfile="${SERVICE_DOCKERFILES[$i]}"
        context="${SERVICE_CONTEXTS[$i]}"
        image="${REGISTRY}${PROJECT_NAME}/${name}:${TAG}"
        
        log "构建: $name"
        docker build -f "$dockerfile" -t "$image" "$context"
    done
    
    log "镜像构建完成"
    echo ""
}

# ==================== 第4步：启动服务 ====================
start_services() {
    log "步骤 4/4: 启动服务"
    echo "----------------------------------------"
    
    # 创建网络
    docker network inspect "${PROJECT_NAME}" >/dev/null 2>&1 || docker network create "${PROJECT_NAME}"
    
    local i
    for i in "${!SERVICE_NAMES[@]}"; do
        name="${SERVICE_NAMES[$i]}"
        port_map="${SERVICE_PORTS[$i]}"
        container="${PROJECT_NAME}-${name}"
        image="${REGISTRY}${PROJECT_NAME}/${name}:${TAG}"
        
        log "启动: $container"
        
        # 构建 docker run 命令
        run_cmd="docker run -d --name $container --network ${PROJECT_NAME}"
        
        # 端口映射
        if [ -n "$port_map" ]; then
            run_cmd="$run_cmd -p ${port_map}"
        fi
        
        # 环境变量文件（后端服务需要）
        if [[ "$name" == backend* ]]; then
            run_cmd="$run_cmd --env-file $ENV_FILE"
        fi
        
        # 重启策略
        run_cmd="$run_cmd --restart unless-stopped"
        
        # 镜像名
        run_cmd="$run_cmd $image"
        
        # 执行
        eval $run_cmd
        
        # 等待一下让服务启动
        sleep 2
    done
    
    echo ""
}

# ==================== 显示状态 ====================
show_status() {
    log "部署完成！"
    echo "========================================"
    echo "标签: $TAG"
    echo ""
    log "运行中的容器:"
    docker ps --filter "name=${PROJECT_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    log "访问地址:"
    local i
    for i in "${!SERVICE_NAMES[@]}"; do
        port_map="${SERVICE_PORTS[$i]}"
        name="${SERVICE_NAMES[$i]}"
        if [ -n "$port_map" ]; then
            host_port=$(echo "$port_map" | cut -d: -f1)
            echo "  $name: http://localhost:$host_port"
        fi
    done
}

# ==================== 主流程 ====================
main() {
    echo "🚀 Smart RAGFlow 部署脚本"
    echo "========================================"
    echo ""
    
    # 检查环境变量文件
    if [ ! -f "$ENV_FILE" ]; then
        err "缺少 $ENV_FILE 文件"
        exit 1
    fi
    
    stop_containers
    remove_old_images
    build_images
    start_services
    show_status
}

# 根据参数执行
usage() {
    echo "用法: $0 [stop|clean|build|start|all]"
    echo ""
    echo "命令:"
    echo "  stop   - 停止所有容器"
    echo "  clean  - 停止容器并删除旧镜像"
    echo "  build  - 构建新镜像"
    echo "  start  - 启动所有服务"
    echo "  all    - 完整部署流程（默认）"
    echo ""
    echo "环境变量:"
    echo "  REGISTRY  - 镜像仓库前缀，如: your-registry.com/"
    echo "  TAG       - 镜像标签，默认: 时间戳 (YYYYMMDD-HHMMSS)"
    echo "  ENV_FILE  - 环境变量文件，默认: .env.docker"
    exit 1
}

case "${1:-all}" in
    stop)
        stop_containers
        ;;
    clean)
        stop_containers
        remove_old_images
        ;;
    build)
        build_images
        ;;
    start)
        start_services
        show_status
        ;;
    all)
        main
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        err "未知命令: $1"
        usage
        ;;
esac
