-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY COMMENT '主键，文档唯一标识（UUID）',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_size BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件内容MD5摘要',
    file_ext VARCHAR(20) NOT NULL COMMENT '文件后缀（如：pdf, docx, txt）',
    file_url VARCHAR(500) NOT NULL COMMENT '文件存入MinIO的URL',
    parse_status TINYINT NOT NULL DEFAULT 0 COMMENT '解析状态：0-未解析, 1-正在解析, 2-解析异常, 3-解析完成',
    parse_message TEXT COMMENT '解析状态消息（异常时记录错误信息）',
    chunk_count INT DEFAULT 0 COMMENT '解析后的分块数量',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_md5 (file_md5),
    INDEX idx_status (parse_status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档表';

-- 解析任务表
CREATE TABLE IF NOT EXISTS parse_tasks (
    id VARCHAR(64) PRIMARY KEY COMMENT '主键，任务唯一标识（UUID）',
    doc_id VARCHAR(64) NOT NULL COMMENT '关联的文档ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_size BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    file_ext VARCHAR(20) NOT NULL COMMENT '文件后缀',
    file_url VARCHAR(500) NOT NULL COMMENT '文件存入MinIO的URL',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件内容MD5摘要',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '解析状态：0-未解析, 1-待解析, 2-解析中, 3-解析异常, 4-解析完成',
    error_message TEXT COMMENT '错误信息',
    started_at TIMESTAMP NULL COMMENT '开始解析时间',
    completed_at TIMESTAMP NULL COMMENT '完成解析时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_doc_id (doc_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解析任务表';

-- 初始化一些测试数据（可选）
-- INSERT INTO documents (id, file_name, file_size, file_md5, file_ext, file_url, parse_status) VALUES
-- ('doc-001', 'test.pdf', 1024000, 'd41d8cd98f00b204e9800998ecf8427e', 'pdf', 'http://minio:9000/bucket/test.pdf', 0);
