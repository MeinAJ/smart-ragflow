-- =====================================================
-- 对话历史表创建脚本
-- 用于存储用户与 AI 的对话历史记录
-- =====================================================

-- 创建对话历史表
CREATE TABLE IF NOT EXISTS `chat_history` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `session_id` VARCHAR(64) NOT NULL COMMENT '会话ID，用于关联同一对话',
    `question` TEXT NOT NULL COMMENT '用户问题',
    `answer` TEXT NOT NULL COMMENT 'AI回答',
    `model` VARCHAR(50) DEFAULT NULL COMMENT '使用的模型名称',
    `tokens_used` INT DEFAULT 0 COMMENT '本次对话消耗的token数',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 主键
    PRIMARY KEY (`id`),
    
    -- 索引
    KEY `idx_session_id` (`session_id`),
    KEY `idx_session_created` (`session_id`, `created_at`)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史记录表';

-- 添加表注释（兼容不同 MySQL 版本）
ALTER TABLE `chat_history` COMMENT = '对话历史记录表 - 存储用户与 AI 的完整对话记录';

-- =====================================================
-- 可选：查看表结构
-- DESCRIBE chat_history;
-- =====================================================
