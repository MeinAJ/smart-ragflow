# Smart RAGFlow 前端

基于 Vue 3 + Vite 的智能问答前端界面。

## 功能特性

- 🚀 流式响应显示 - 实时展示 AI 回复
- 📝 Markdown 渲染 - 支持代码高亮、表格等
- 💬 聊天界面 - 类 ChatGPT 的交互体验
- 🎨 响应式设计 - 美观的 UI 界面

## 技术栈

- Vue 3 (Composition API)
- Vite
- Marked (Markdown 渲染)
- Highlight.js (代码高亮)

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

前端服务将运行在 http://localhost:3000

代理配置：
- `/v1` → `http://localhost:8000` (后端 API)

### 构建

```bash
npm run build
```

## 目录结构

```
frontend/
├── src/
│   ├── components/
│   │   └── ChatMessage.vue    # 聊天消息组件
│   ├── views/
│   │   └── ChatView.vue       # 聊天页面
│   ├── utils/
│   │   └── api.js             # API 工具
│   ├── App.vue                # 根组件
│   └── main.js                # 入口
├── index.html
├── package.json
└── vite.config.js
```

## 接口说明

前端调用 `/v1/chat/completions` 接口：

```javascript
POST /v1/chat/completions
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "问题" }
  ],
  "stream": true
}
```

响应：SSE 流式格式
```
data: {"choices": [{"delta": {"content": "片段"}}]}
data: [DONE]
```
