-- ========================================================
-- Smart RAGFlow Database Initialization Script
-- 数据库初始化脚本
-- 
-- 包含所有表的 CREATE TABLE 语句
-- 字符集: utf8mb4 (支持完整的 Unicode 字符，包括 emoji)
-- 引擎: InnoDB (支持事务、外键、行级锁)
-- ========================================================

-- 设置字符集和引擎
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ========================================================
-- 1. 用户表 (users)
-- 存储用户信息和认证数据
-- ========================================================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名',
    `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希（bcrypt加密）',
    `nickname` VARCHAR(50) DEFAULT NULL COMMENT '昵称',
    `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活：1-是，0-否',
    `is_admin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否管理员：1-是，0-否',
    `last_login_at` DATETIME DEFAULT NULL COMMENT '最后登录时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_username` (`username`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';


-- ========================================================
-- 2. 文档表 (documents)
-- 存储文档元数据和解析状态
-- ========================================================
DROP TABLE IF EXISTS `documents`;
CREATE TABLE `documents` (
    `id` VARCHAR(64) NOT NULL COMMENT '主键，UUID格式',
    `file_name` VARCHAR(255) NOT NULL COMMENT '文件名',
    `file_size` BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    `file_md5` VARCHAR(32) NOT NULL COMMENT '文件MD5摘要，用于去重',
    `file_ext` VARCHAR(20) NOT NULL COMMENT '文件后缀，如 pdf, docx',
    `file_url` VARCHAR(500) NOT NULL COMMENT 'MinIO文件存储URL',
    `parse_status` SMALLINT NOT NULL DEFAULT 0 COMMENT '解析状态：0-未解析，1-正在解析，2-解析异常，3-解析完成',
    `parse_message` TEXT COMMENT '解析状态消息或错误信息',
    `chunk_count` INT NOT NULL DEFAULT 0 COMMENT '分块数量（解析完成后更新）',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_parse_status` (`parse_status`),
    KEY `idx_file_md5` (`file_md5`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';


-- ========================================================
-- 3. 解析任务表 (parse_tasks)
-- 存储文档解析任务队列
-- ========================================================
DROP TABLE IF EXISTS `parse_tasks`;
CREATE TABLE `parse_tasks` (
    `id` VARCHAR(64) NOT NULL COMMENT '主键，UUID格式',
    `doc_id` VARCHAR(64) NOT NULL COMMENT '关联的文档ID',
    `file_name` VARCHAR(255) NOT NULL COMMENT '文件名',
    `file_size` BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    `file_ext` VARCHAR(20) NOT NULL COMMENT '文件后缀',
    `file_url` VARCHAR(500) NOT NULL COMMENT 'MinIO文件URL',
    `file_md5` VARCHAR(32) NOT NULL COMMENT '文件MD5摘要',
    `status` SMALLINT NOT NULL DEFAULT 0 COMMENT '解析状态：0-未解析，1-待解析，2-解析中，3-解析异常，4-解析完成',
    `error_message` TEXT COMMENT '错误信息（解析失败时）',
    `started_at` DATETIME DEFAULT NULL COMMENT '开始解析时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成解析时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_doc_id` (`doc_id`),
    KEY `idx_status` (`status`),
    KEY `idx_status_created` (`status`, `created_at`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解析任务表';


-- ========================================================
-- 4. 对话历史表 (chat_history)
-- 存储用户提问和AI回答的消息记录
-- ========================================================
DROP TABLE IF EXISTS `chat_history`;
CREATE TABLE `chat_history` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `session_id` VARCHAR(64) NOT NULL COMMENT '会话ID，用于关联同一对话',
    `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '角色类型：user-用户，assistant-AI助手',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `model` VARCHAR(50) DEFAULT NULL COMMENT '使用的模型名称，如 deepseek-chat',
    `tokens_used` INT NOT NULL DEFAULT 0 COMMENT '本次消息消耗的token数',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_session_id` (`session_id`),
    KEY `idx_user_session` (`user_id`, `session_id`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    KEY `idx_session_role` (`session_id`, `role`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';


-- ========================================================
-- 5. 用户会话表 (user_session)
-- 存储用户的会话信息，每个会话对应一个对话线程
-- ========================================================
DROP TABLE IF EXISTS `user_session`;
CREATE TABLE `user_session` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `session_id` VARCHAR(64) NOT NULL COMMENT '会话ID，UUID格式',
    `session_name` VARCHAR(200) DEFAULT NULL COMMENT '会话名称，用户可自定义',
    `message_count` INT NOT NULL DEFAULT 0 COMMENT '消息数量',
    `last_message_at` DATETIME DEFAULT NULL COMMENT '最后一条消息时间',
    `is_pinned` SMALLINT NOT NULL DEFAULT 0 COMMENT '是否置顶：0-否，1-是',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_session_id` (`session_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_user_last_msg` (`user_id`, `last_message_at`),
    KEY `idx_user_pinned` (`user_id`, `is_pinned`, `last_message_at`),
    KEY `idx_last_message_at` (`last_message_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';


-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;


-- ========================================================
-- 初始化数据
-- ========================================================

-- 创建默认管理员账号（密码需替换为实际的 bcrypt 哈希值）
-- 默认密码: admin123
-- INSERT INTO `users` (`username`, `email`, `password_hash`, `nickname`, `is_admin`, `is_active`) 
-- VALUES ('admin', 'admin@example.com', '$2b$12$...', '管理员', 1, 1);
