# Smart RAGFlow - 文档管理系统

文档管理后台，支持文档的增删改查和解析功能。

## 功能特性

- 📤 **文档上传** - 支持多种格式（PDF、DOCX、TXT、MD、XLSX、PPTX 等）
- 📋 **文档列表** - 分页展示、搜索筛选
- 📝 **文档编辑** - 修改文档标题和描述
- 🗑️ **文档删除** - 支持单条删除
- ▶️ **文档解析** - 触发文档向量化解析流程
- 📊 **状态管理** - 实时查看文档解析状态

## 5个核心接口

| 序号 | 接口 | 方法 | 描述 |
|------|------|------|------|
| 1 | `/api/documents` | GET | 查询文档列表 |
| 2 | `/api/documents` | POST | 上传/创建文档 |
| 3 | `/api/documents/{doc_id}` | DELETE | 删除文档 |
| 4 | `/api/documents/{doc_id}` | PUT | 更新文档信息 |
| 5 | `/api/documents/{doc_id}/parse` | POST | 解析文档 |

## 技术栈

- Vue 3
- Element Plus
- Axios
- Vite

## 快速开始

### 安装依赖

```bash
cd frontend-admin
npm install
```

### 开发模式

```bash
npm run dev
```

服务将运行在 http://localhost:3001

### 构建

```bash
npm run build
```

## 目录结构

```
frontend-admin/
├── src/
│   ├── api/
│   │   └── documents.js    # 5个核心接口
│   ├── views/
│   │   └── DocumentManager.vue  # 文档管理页面
│   ├── App.vue
│   └── main.js
├── package.json
├── vite.config.js
└── README.md
```

## 代理配置

开发服务器已配置代理，将 `/api` 请求转发到后端服务 `http://localhost:8000`：

```javascript
// vite.config.js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

## 关联系统

- **问答系统**: http://localhost:3000 (frontend-QA)
- **后端服务**: http://localhost:8000
