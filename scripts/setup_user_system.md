# 用户系统和会话隔离配置指南

## 1. 数据库迁移

执行 SQL 迁移脚本：

```bash
# 进入项目目录
cd /Users/ja/project/python/smart-ragflow

# 登录 MySQL 并执行迁移脚本
mysql -u root -p ragflow < scripts/migrate_user_system.sql
```

## 2. 安装后端依赖

```bash
cd /Users/ja/project/python/smart-ragflow
uv pip install -e "."
```

或手动安装依赖：
```bash
uv pip install python-jose[cryptography] passlib[bcrypt]
```

## 3. 启动后端服务

```bash
cd /Users/ja/project/python/smart-ragflow/backend_QA
uv run python -m main
```

后端服务将在 http://localhost:8000 启动

## 4. 启动前端服务

```bash
cd /Users/ja/project/python/smart-ragflow/frontend_QA
npm run dev
```

前端服务将在 http://localhost:3000 启动

## 5. 测试步骤

### 5.1 用户注册
1. 访问 http://localhost:3000
2. 系统会自动跳转到登录页
3. 点击"注册"标签
4. 输入用户名（至少3位）、密码（至少6位）
5. 点击注册按钮
6. 注册成功后会自动登录并跳转到聊天页面

### 5.2 用户登录
1. 访问 http://localhost:3000/login
2. 输入用户名和密码
3. 点击登录
4. 使用默认测试账号：
   - 管理员账号：`admin` / `admin123`
   - 测试账号：`test` / `test123`

### 5.3 会话功能测试
1. **创建新会话**：点击左侧"开启新对话"按钮
2. **发送消息**：在输入框输入问题，按 Enter 发送
3. **查看历史会话**：左侧列表会显示历史会话，按时间分组（今天、昨天、7天内、更早）
4. **切换会话**：点击历史会话可以查看之前的对话并继续对话
5. **删除会话**：点击会话项右侧的删除按钮

### 5.4 用户隔离测试
1. 使用用户A登录，创建一些会话
2. 退出登录，使用用户B登录
3. 验证用户B看不到用户A的会话历史
4. 用户B创建自己的会话

## 6. API 端点

### 认证接口
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `GET /auth/me` - 获取当前用户信息
- `POST /auth/logout` - 用户登出

### 聊天接口（需要认证）
- `POST /v1/chat/completions` - 流式问答

### 历史记录接口（需要认证）
- `GET /history/sessions` - 获取用户会话列表
- `GET /history/sessions/{session_id}` - 获取会话详情
- `GET /history/sessions/{session_id}/messages` - 获取会话消息
- `DELETE /history/sessions/{session_id}` - 删除会话

## 7. 数据库表结构

### users 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| username | VARCHAR(50) | 用户名，唯一 |
| email | VARCHAR(100) | 邮箱，唯一，可选 |
| password_hash | VARCHAR(255) | 密码哈希 |
| nickname | VARCHAR(50) | 昵称 |
| avatar | VARCHAR(500) | 头像URL |
| is_active | BOOLEAN | 是否激活 |
| is_admin | BOOLEAN | 是否管理员 |
| last_login_at | DATETIME | 最后登录时间 |
| created_at | DATETIME | 创建时间 |

### chat_history 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键，自增 |
| user_id | BIGINT | 用户ID，外键 |
| session_id | VARCHAR(64) | 会话ID |
| role | VARCHAR(20) | 角色：user/assistant |
| content | TEXT | 消息内容 |
| model | VARCHAR(50) | 模型名称 |
| tokens_used | INT | Token消耗 |
| created_at | DATETIME | 创建时间 |

## 8. 注意事项

1. **JWT Secret**：生产环境请修改 `backend_QA/api/auth.py` 中的 `SECRET_KEY`
2. **密码安全**：默认密码使用 bcrypt 加密
3. **Token 有效期**：默认 7 天
4. **CORS**：开发环境允许所有来源，生产环境请限制域名

## 9. 故障排查

### 登录失败
- 检查后端服务是否启动
- 检查浏览器控制台网络请求
- 确认用户名密码正确

### 会话列表为空
- 确认用户已登录（检查 localStorage 中的 token）
- 检查后端 API 返回数据

### 无法发送消息
- 检查网络连接
- 确认 session_id 生成正确
- 查看后端日志
