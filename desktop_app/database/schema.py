from __future__ import annotations


SCHEMA_VERSION = 16

CREATE_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at REAL NOT NULL
);
"""

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    root_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    archived_at REAL
);
"""

CREATE_PROJECTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""

CREATE_PROVIDER_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS provider_profiles (
    id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    embedding_model TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""

CREATE_PROVIDER_PROFILES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_provider_profiles_provider_name ON provider_profiles(provider_name);
CREATE INDEX IF NOT EXISTS idx_provider_profiles_enabled ON provider_profiles(enabled);
"""

CREATE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    duration REAL NOT NULL,
    fps REAL NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    thumbnail_path TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, file_path)
);
"""

CREATE_VIDEOS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_videos_project_id ON videos(project_id);
CREATE INDEX IF NOT EXISTS idx_videos_name ON videos(name);
CREATE INDEX IF NOT EXISTS idx_videos_updated_at ON videos(updated_at);
"""

CREATE_TRANSCRIPTS_TABLE = """
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

CREATE_TRANSCRIPT_SEGMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS transcript_segments (
    id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);
"""

CREATE_TRANSCRIPTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_transcripts_video_id ON transcripts(video_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_status ON transcripts(status);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_transcript_id ON transcript_segments(transcript_id);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_start_time ON transcript_segments(start_time);
"""

CREATE_KNOWLEDGE_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    chunk_text TEXT NOT NULL,
    topic_title TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    word_count INTEGER NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);
"""

CREATE_CHUNK_TOPICS_TABLE = """
CREATE TABLE IF NOT EXISTS chunk_topics (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    topic_title TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE
);
"""

CREATE_KNOWLEDGE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_transcript_id ON knowledge_chunks(transcript_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_start_time ON knowledge_chunks(start_time);
CREATE INDEX IF NOT EXISTS idx_chunk_topics_chunk_id ON chunk_topics(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_topics_topic_title ON chunk_topics(topic_title);
"""

CREATE_EMBEDDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding_blob BLOB NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE,
    UNIQUE(chunk_id, model_name)
);
"""

CREATE_EMBEDDINGS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model_name ON embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at ON embeddings(created_at);
"""

CREATE_VECTOR_INDEXES_TABLE = """
CREATE TABLE IF NOT EXISTS vector_indexes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    index_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_VECTOR_INDEXES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_vector_indexes_project_id ON vector_indexes(project_id);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_embedding_model ON vector_indexes(embedding_model);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_updated_at ON vector_indexes(updated_at);
"""

CREATE_RETRIEVAL_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS retrieval_history (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    query TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    duration_ms REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_RETRIEVAL_HISTORY_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_retrieval_history_project_id ON retrieval_history(project_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_history_embedding_model ON retrieval_history(embedding_model);
CREATE INDEX IF NOT EXISTS idx_retrieval_history_created_at ON retrieval_history(created_at);
"""

CREATE_EVIDENCE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS evidence_history (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    query TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE
);
"""

CREATE_EVIDENCE_HISTORY_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_evidence_history_project_id ON evidence_history(project_id);
CREATE INDEX IF NOT EXISTS idx_evidence_history_query ON evidence_history(query);
CREATE INDEX IF NOT EXISTS idx_evidence_history_chunk_id ON evidence_history(chunk_id);
CREATE INDEX IF NOT EXISTS idx_evidence_history_created_at ON evidence_history(created_at);
"""

CREATE_CHAT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS chat_history (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    provider TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_CHAT_HISTORY_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_chat_history_project_id ON chat_history(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_provider ON chat_history(provider);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at);
"""

CREATE_CHAT_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    last_message_at REAL,
    deleted_at REAL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_CHAT_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_model TEXT NOT NULL DEFAULT '',
    duration_ms REAL NOT NULL,
    token_usage_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_CHAT_SESSION_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_chat_sessions_project_id ON chat_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_message_at ON chat_sessions(last_message_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_project_id ON chat_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_provider ON chat_messages(provider);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
"""

CREATE_COMPARE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS compare_sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    session_name TEXT NOT NULL,
    videos_json TEXT NOT NULL,
    query TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_COMPARE_SESSIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_compare_sessions_project_id ON compare_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_compare_sessions_created_at ON compare_sessions(created_at);
"""

CREATE_BOOKMARKS_TABLE = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    video_id TEXT NOT NULL DEFAULT '',
    chunk_id TEXT NOT NULL DEFAULT '',
    transcript_id TEXT NOT NULL DEFAULT '',
    segment_id TEXT NOT NULL DEFAULT '',
    bookmark_type TEXT NOT NULL,
    title TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    timestamp REAL NOT NULL DEFAULT 0.0,
    source_text TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_HIGHLIGHTS_TABLE = """
CREATE TABLE IF NOT EXISTS highlights (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    video_id TEXT NOT NULL DEFAULT '',
    transcript_id TEXT NOT NULL DEFAULT '',
    segment_id TEXT NOT NULL DEFAULT '',
    chunk_id TEXT NOT NULL DEFAULT '',
    highlighted_text TEXT NOT NULL,
    color TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    timestamp REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_BOOKMARK_HIGHLIGHT_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_bookmarks_project_id ON bookmarks(project_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_video_id ON bookmarks(video_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_chunk_id ON bookmarks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at ON bookmarks(created_at);
CREATE INDEX IF NOT EXISTS idx_highlights_project_id ON highlights(project_id);
CREATE INDEX IF NOT EXISTS idx_highlights_video_id ON highlights(video_id);
CREATE INDEX IF NOT EXISTS idx_highlights_transcript_id ON highlights(transcript_id);
CREATE INDEX IF NOT EXISTS idx_highlights_chunk_id ON highlights(chunk_id);
CREATE INDEX IF NOT EXISTS idx_highlights_created_at ON highlights(created_at);
"""

CREATE_PROVIDER_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS provider_usage (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    task_type TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    response_time_ms REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

CREATE_PROVIDER_USAGE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_provider_usage_project_id ON provider_usage(project_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_provider ON provider_usage(provider);
CREATE INDEX IF NOT EXISTS idx_provider_usage_created_at ON provider_usage(created_at);
"""

CREATE_PROVIDER_BENCHMARKS_TABLE = """
CREATE TABLE IF NOT EXISTS provider_benchmarks (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    task_type TEXT NOT NULL,
    success INTEGER NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    error_message TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
"""

CREATE_PROVIDER_BENCHMARKS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_provider_benchmarks_provider ON provider_benchmarks(provider);
CREATE INDEX IF NOT EXISTS idx_provider_benchmarks_task_type ON provider_benchmarks(task_type);
CREATE INDEX IF NOT EXISTS idx_provider_benchmarks_created_at ON provider_benchmarks(created_at);
"""

CREATE_PROVIDER_HEALTH_CHECKS_TABLE = """
CREATE TABLE IF NOT EXISTS provider_health_checks (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    profile_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    configured INTEGER NOT NULL,
    reachable INTEGER NOT NULL,
    authentication_valid INTEGER NOT NULL,
    model_available INTEGER NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    message TEXT NOT NULL DEFAULT '',
    checked_at REAL NOT NULL
);
"""

CREATE_PROVIDER_HEALTH_CHECKS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_provider_health_checks_provider ON provider_health_checks(provider);
CREATE INDEX IF NOT EXISTS idx_provider_health_checks_profile_id ON provider_health_checks(profile_id);
CREATE INDEX IF NOT EXISTS idx_provider_health_checks_checked_at ON provider_health_checks(checked_at);
"""
