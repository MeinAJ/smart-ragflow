#!/bin/bash

# 强制删除 smart-ragflow 项目的 5 个容器

echo "正在强制删除容器..."

docker rm -f smart-ragflow-backend-qa smart-ragflow-backend-admin smart-ragflow-backend-parser smart-ragflow-frontend-qa smart-ragflow-frontend-admin

echo "容器已删除"
