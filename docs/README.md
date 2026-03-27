# Smart RAGFlow 文档中心

欢迎来到 Smart RAGFlow 文档中心！这里汇集了项目的完整文档资源。

## 快速开始

如果你是第一次接触本项目，建议按以下顺序阅读：

1. **[项目 README](../README.md)** - 项目简介、快速开始指南
2. **[架构文档](ARCHITECTURE.md)** - 深入理解系统设计
3. **[API 文档](API_DOCUMENTATION.md)** - 接口使用参考

## 文档目录

### 📚 核心文档

| 文档 | 说明 | 适合读者 |
|------|------|----------|
| [README.md](../README.md) | 项目概览、快速开始 | 所有人 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构、模块设计 | 开发者、架构师 |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API 接口详细说明 | 前端开发、API 使用者 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署、运维指南 | 运维人员、DevOps |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 开发贡献指南 | 贡献者、开发者 |

### 🔧 开发指南

- **环境搭建** - 见 [CONTRIBUTING.md](CONTRIBUTING.md#开发环境搭建)
- **代码规范** - 见 [CONTRIBUTING.md](CONTRIBUTING.md#代码规范)
- **调试技巧** - 见 [CONTRIBUTING.md](CONTRIBUTING.md#调试技巧)

### 📖 模块文档

#### Backend QA (问答服务)

| 模块 | 路径 | 说明 |
|------|------|------|
| RAG Graph | `backend_QA/core/graph.py` | LangGraph 流程定义 |
| Nodes | `backend_QA/core/nodes.py` | 向量化、检索、重排序、生成节点 |
| State | `backend_QA/core/state.py` | 状态定义 |
| MMR Service | `backend_QA/services/mmr.py` | MMR 重排序算法 |
| Embedding | `backend_QA/services/embedding.py` | 向量化服务 |
| LLM | `backend_QA/services/llm.py` | LLM 客户端 |

#### Backend Parser (解析服务)

| 模块 | 路径 | 说明 |
|------|------|------|
| Worker | `backend_parser/worker.py` | 后台任务处理 |
| Parser | `backend_parser/deepdoc_parser.py` | 文档解析 |
| Chunker | `backend_parser/chunker.py` | 文本分块 |

### 🚀 部署指南

- **Docker 部署** - 见 [DEPLOYMENT.md](DEPLOYMENT.md#docker-部署推荐)
- **手动部署** - 见 [DEPLOYMENT.md](DEPLOYMENT.md#手动部署)
- **配置优化** - 见 [DEPLOYMENT.md](DEPLOYMENT.md#配置优化)

## 常见问题

### 我是新手，从哪里开始？

建议按以下步骤：
1. 阅读 [项目 README](../README.md) 了解项目是什么
2. 跟着 README 的"快速开始"搭建开发环境
3. 阅读 [架构文档](ARCHITECTURE.md) 理解系统工作原理
4. 查看 [API 文档](API_DOCUMENTATION.md) 了解如何调用接口

### 我想贡献代码，需要做什么？

1. 阅读 [贡献指南](CONTRIBUTING.md)
2. 搭建开发环境
3. 查看 [Issues](https://github.com/your-org/smart-ragflow/issues) 寻找任务
4. 提交 Pull Request

### 我要部署到生产环境，需要注意什么？

1. 阅读 [部署文档](DEPLOYMENT.md)
2. 修改默认密码和 JWT 密钥
3. 配置 HTTPS
4. 设置监控和日志收集
5. 配置备份策略

## 文档更新

本文档随代码一起维护。如果发现文档有误或需要更新，欢迎提交 PR。

## 获取帮助

- **GitHub Issues**: 报告 Bug 或提出功能建议
- **GitHub Discussions**: 讨论使用问题和最佳实践
- **Email**: dev@your-org.com

---

**提示**: 本文档使用 Markdown 格式编写，建议使用支持 Markdown 的编辑器阅读以获得最佳体验。
