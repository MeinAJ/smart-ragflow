-- chat_history 表结构迁移脚本
-- 用于将旧表结构（question/answer）迁移到新结构（role/content）
-- 执行前请备份数据！！！

-- ============================================
-- 步骤 1: 查看当前表结构
-- ============================================
DESCRIBE chat_history;

-- ============================================
-- 步骤 2: 修改表和列为 utf8mb4 字符集（解决中文编码问题）
-- ============================================
ALTER TABLE chat_history CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 如果存在 question/answer 列，修改它们的字符集
ALTER TABLE chat_history 
    MODIFY COLUMN question TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY COLUMN answer TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ============================================
-- 步骤 3: 添加新列（role, content）
-- ============================================
ALTER TABLE chat_history 
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '角色类型：user/assistant',
    ADD COLUMN IF NOT EXISTS content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '消息内容';

-- ============================================
-- 步骤 4: 添加索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_session_role ON chat_history(session_id, role);

-- ============================================
-- 步骤 5: 迁移旧数据（将 question/answer 转换为 role/content）
-- ============================================

-- 先创建临时表存储旧数据
CREATE TABLE IF NOT EXISTS chat_history_backup AS 
SELECT * FROM chat_history WHERE 1=0;

-- 备份数据
INSERT INTO chat_history_backup SELECT * FROM chat_history;

-- 清空原表（准备重新插入数据）
-- 注意：这里使用 DELETE 而不是 TRUNCATE，因为可能有外键约束
DELETE FROM chat_history;

-- 重置自增ID（可选）
-- ALTER TABLE chat_history AUTO_INCREMENT = 1;

-- 插入用户消息（role='user', content=question）
INSERT INTO chat_history (session_id, role, content, model, tokens_used, created_at)
SELECT 
    session_id, 
    'user' as role, 
    question as content, 
    model, 
    IF(tokens_used > 0, tokens_used DIV 2, 0) as tokens_used, 
    created_at
FROM chat_history_backup 
WHERE question IS NOT NULL AND question != '';

-- 插入AI消息（role='assistant', content=answer）
INSERT INTO chat_history (session_id, role, content, model, tokens_used, created_at)
SELECT 
    session_id, 
    'assistant' as role, 
    answer as content, 
    model, 
    IF(tokens_used > 0, tokens_used DIV 2, 0) as tokens_used, 
    created_at
FROM chat_history_backup 
WHERE answer IS NOT NULL AND answer != '';

-- ============================================
-- 步骤 6: 删除旧列（确认数据迁移成功后执行）
-- ============================================
-- ALTER TABLE chat_history DROP COLUMN question;
-- ALTER TABLE chat_history DROP COLUMN answer;

-- ============================================
-- 步骤 7: 修改 content 列为非空
-- ============================================
-- ALTER TABLE chat_history MODIFY COLUMN content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息内容';

-- ============================================
-- 验证：查看新表结构和数据
-- ============================================
DESCRIBE chat_history;
SELECT role, LEFT(content, 50) as content_preview, created_at FROM chat_history ORDER BY created_at DESC LIMIT 10;

-- 删除临时表（确认无误后执行）
-- DROP TABLE chat_history_backup;
