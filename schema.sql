-- ==========================================================
-- Pragati Bharati Document Intelligence Service
-- Database Schema (PostgreSQL & SQLite compatible DDL)
-- ==========================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 2. Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    document_type VARCHAR(20) NOT NULL, -- PDF, IMAGE
    document_role VARCHAR(50) DEFAULT 'QUESTION_PAPER', -- QUESTION_PAPER, ANSWER_KEY, COMBINED
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,
    page_count INTEGER DEFAULT 0,
    ocr_method_used VARCHAR(100) DEFAULT 'heuristic_parser',
    total_questions INTEGER DEFAULT 0,
    confident_questions INTEGER DEFAULT 0,
    review_required_questions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- 3. Document Relations Table (For linking Question Papers with Answer Keys)
CREATE TABLE IF NOT EXISTS document_relations (
    id VARCHAR(36) PRIMARY KEY,
    source_document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) DEFAULT 'ANSWER_KEY_FOR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON document_relations(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON document_relations(target_document_id);

-- 4. Questions Table
CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    question_number INTEGER,
    raw_number_label VARCHAR(50),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'MULTIPLE_CHOICE',
    source_pages JSON, -- JSON array of pages e.g. [1, 2]
    confidence_score FLOAT DEFAULT 1.0,
    confidence_level VARCHAR(20) DEFAULT 'CONFIDENT', -- CONFIDENT, PARTIAL, NEEDS_REVIEW
    review_reasons JSON, -- JSON array of flags
    detected_answer VARCHAR(100),
    answer_explanation TEXT,
    answer_source VARCHAR(100),
    has_images_or_tables BOOLEAN DEFAULT FALSE,
    metadata_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_questions_doc_id ON questions(document_id);
CREATE INDEX IF NOT EXISTS idx_questions_q_num ON questions(question_number);
CREATE INDEX IF NOT EXISTS idx_questions_conf_level ON questions(confidence_level);

-- 5. Question Options Table
CREATE TABLE IF NOT EXISTS options (
    id VARCHAR(36) PRIMARY KEY,
    question_id VARCHAR(36) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    option_key VARCHAR(10) NOT NULL, -- A, B, C, D
    option_text TEXT NOT NULL,
    is_correct BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_options_question_id ON options(question_id);

-- 6. Answer Key Entries Table
CREATE TABLE IF NOT EXISTS answer_key_entries (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    correct_answer VARCHAR(100) NOT NULL,
    explanation TEXT,
    source_page INTEGER DEFAULT 1,
    raw_text VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ak_doc_id ON answer_key_entries(document_id);
CREATE INDEX IF NOT EXISTS idx_ak_q_num ON answer_key_entries(question_number);

-- 7. Processing Logs Table
CREATE TABLE IF NOT EXISTS processing_logs (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    stage VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    level VARCHAR(20) DEFAULT 'INFO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_doc_id ON processing_logs(document_id);
