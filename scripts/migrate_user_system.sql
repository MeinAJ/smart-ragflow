-- 用户系统和会话历史用户隔离迁移脚本
-- 执行前请备份数据！！！

-- ============================================
-- 1. 创建 users 表
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    email VARCHAR(100) COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    nickname VARCHAR(50) COMMENT '昵称',
    avatar VARCHAR(500) COMMENT '头像URL',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_admin BOOLEAN DEFAULT FALSE COMMENT '是否管理员',
    last_login_at DATETIME COMMENT '最后登录时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 2. 修改 chat_history 表，添加 user_id 字段
-- ============================================

-- 先检查 chat_history 表是否存在
SET @dbname = DATABASE();
SET @tablename = 'chat_history';

-- 检查表是否存在
SELECT COUNT(*) INTO @table_exists
FROM information_schema.tables 
WHERE table_schema = @dbname AND table_name = @tablename;

-- 如果表不存在，创建新表
SET @create_table = IF(@table_exists = 0, 
    'CREATE TABLE chat_history (
        id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT "自增主键ID",
        user_id BIGINT NOT NULL COMMENT "用户ID",
        session_id VARCHAR(64) NOT NULL COMMENT "会话ID",
        role VARCHAR(20) NOT NULL DEFAULT "user" COMMENT "角色类型",
        content TEXT NOT NULL COMMENT "消息内容",
        model VARCHAR(50) COMMENT "使用的模型名称",
        tokens_used INT DEFAULT 0 COMMENT "消耗的token数",
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间",
        KEY idx_user_session (user_id, session_id),
        KEY idx_user_created (user_id, created_at),
        KEY idx_session_role (session_id, role)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="对话历史记录表"',
    'SELECT "chat_history table already exists" as message');
    
PREPARE stmt FROM @create_table;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 如果表存在，添加 user_id 字段
SELECT COUNT(*) INTO @has_user_id
FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = @tablename AND column_name = 'user_id';

SET @add_user_id = IF(@has_user_id = 0 AND @table_exists > 0,
    'ALTER TABLE chat_history ADD COLUMN user_id BIGINT NOT NULL DEFAULT 1 COMMENT "用户ID" AFTER id',
    'SELECT "user_id column already exists or table not exists" as message');

PREPARE stmt FROM @add_user_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_user_session ON chat_history(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_user_created ON chat_history(user_id, created_at);

-- ============================================
-- 3. 创建默认管理员用户（密码：admin123）
-- ============================================
-- 注意：生产环境请修改默认密码
INSERT INTO users (username, email, password_hash, nickname, is_admin, is_active)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1q',
    '管理员',
    TRUE,
    TRUE
) ON DUPLICATE KEY UPDATE id=id;

-- ============================================
-- 4. 创建测试用户（密码：test123）
-- ============================================
INSERT INTO users (username, email, password_hash, nickname, is_active)
VALUES (
    'test',
    'test@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1q',
    '测试用户',
    TRUE
) ON DUPLICATE KEY UPDATE id=id;

-- 查看结果
SELECT 'Users created:' as info;
SELECT id, username, email, nickname, is_admin, is_active FROM users;

SELECT 'Table structure:' as info;
DESCRIBE chat_history;

-- ============================================
-- 如果需要迁移旧数据，执行以下步骤：
-- ============================================
-- 
-- 1. 更新旧数据的 user_id（默认设置为 1）
-- UPDATE chat_history SET user_id = 1 WHERE user_id IS NULL;
--
-- 2. 删除默认值约束（如果需要）
-- ALTER TABLE chat_history ALTER COLUMN user_id DROP DEFAULT;
