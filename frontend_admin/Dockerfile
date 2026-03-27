# Frontend Admin - Vue3 管理后台 (端口 8080)
# 多阶段构建：Node 构建 + Nginx 服务

# =================== 阶段1：构建 ===================
FROM node:18-alpine AS builder

WORKDIR /app

# 复制依赖文件（利用缓存层）
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# =================== 阶段2：运行 ===================
FROM nginx:alpine

# 创建自定义 Nginx 配置（添加反向代理到 backend）
RUN echo 'server { \
    listen 8080; \
    \
    # API 反向代理到 backend-admin \
    location /api { \
        proxy_pass http://smart-ragflow-backend-admin:8001; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_read_timeout 300s; \
    } \
    \
    # 静态文件服务 \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf && \
    # 修改 nginx.conf 使用 /tmp 目录 \
    sed -i 's|/run/nginx.pid|/tmp/nginx.pid|g' /etc/nginx/nginx.conf && \
    sed -i 's|^user.*;|user nginx;|g' /etc/nginx/nginx.conf && \
    # 创建目录并设置权限 \
    mkdir -p /tmp /var/cache/nginx /var/log/nginx && \
    chown -R nginx:nginx /tmp /var/cache/nginx /var/log/nginx /etc/nginx/conf.d /usr/share/nginx/html

# 从 builder 复制构建产物
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# 切换到非 root 用户
USER nginx

# 暴露端口（非特权端口）
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
