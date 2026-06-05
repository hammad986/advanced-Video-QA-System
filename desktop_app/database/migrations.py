from __future__ import annotations

import time
from dataclasses import dataclass
from sqlite3 import Connection

from desktop_app.database import schema


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="create_projects_table",
        statements=(
            schema.CREATE_SCHEMA_MIGRATIONS,
            schema.CREATE_PROJECTS_TABLE,
            schema.CREATE_PROJECTS_INDEXES,
        ),
    ),
    Migration(
        version=2,
        name="create_settings_and_provider_profiles",
        statements=(
            schema.CREATE_SETTINGS_TABLE,
            schema.CREATE_PROVIDER_PROFILES_TABLE,
            schema.CREATE_PROVIDER_PROFILES_INDEXES,
        ),
    ),
    Migration(
        version=3,
        name="create_videos_table",
        statements=(
            schema.CREATE_VIDEOS_TABLE,
            schema.CREATE_VIDEOS_INDEXES,
        ),
    ),
    Migration(
        version=4,
        name="create_transcript_tables",
        statements=(
            schema.CREATE_TRANSCRIPTS_TABLE,
            schema.CREATE_TRANSCRIPT_SEGMENTS_TABLE,
            schema.CREATE_TRANSCRIPTS_INDEXES,
        ),
    ),
    Migration(
        version=5,
        name="create_knowledge_tables",
        statements=(
            schema.CREATE_KNOWLEDGE_CHUNKS_TABLE,
            schema.CREATE_CHUNK_TOPICS_TABLE,
            schema.CREATE_KNOWLEDGE_INDEXES,
        ),
    ),
    Migration(
        version=6,
        name="create_embeddings_table",
        statements=(
            schema.CREATE_EMBEDDINGS_TABLE,
            schema.CREATE_EMBEDDINGS_INDEXES,
        ),
    ),
    Migration(
        version=7,
        name="create_vector_indexes_table",
        statements=(
            schema.CREATE_VECTOR_INDEXES_TABLE,
            schema.CREATE_VECTOR_INDEXES_INDEXES,
        ),
    ),
    Migration(
        version=8,
        name="create_retrieval_history_table",
        statements=(
            schema.CREATE_RETRIEVAL_HISTORY_TABLE,
            schema.CREATE_RETRIEVAL_HISTORY_INDEXES,
        ),
    ),
    Migration(
        version=9,
        name="create_evidence_history_table",
        statements=(
            schema.CREATE_EVIDENCE_HISTORY_TABLE,
            schema.CREATE_EVIDENCE_HISTORY_INDEXES,
        ),
    ),
    Migration(
        version=10,
        name="create_chat_history_table",
        statements=(
            schema.CREATE_CHAT_HISTORY_TABLE,
            schema.CREATE_CHAT_HISTORY_INDEXES,
        ),
    ),
    Migration(
        version=11,
        name="create_chat_session_tables",
        statements=(
            schema.CREATE_CHAT_SESSIONS_TABLE,
            schema.CREATE_CHAT_MESSAGES_TABLE,
            schema.CREATE_CHAT_SESSION_INDEXES,
        ),
    ),
    Migration(
        version=12,
        name="create_compare_sessions_table",
        statements=(
            schema.CREATE_COMPARE_SESSIONS_TABLE,
            schema.CREATE_COMPARE_SESSIONS_INDEXES,
        ),
    ),
    Migration(
        version=13,
        name="create_bookmark_highlight_tables",
        statements=(
            schema.CREATE_BOOKMARKS_TABLE,
            schema.CREATE_HIGHLIGHTS_TABLE,
            schema.CREATE_BOOKMARK_HIGHLIGHT_INDEXES,
        ),
    ),
    Migration(
        version=14,
        name="create_provider_usage_table",
        statements=(
            schema.CREATE_PROVIDER_USAGE_TABLE,
            schema.CREATE_PROVIDER_USAGE_INDEXES,
        ),
    ),
    Migration(
        version=15,
        name="create_provider_benchmarks_table",
        statements=(
            schema.CREATE_PROVIDER_BENCHMARKS_TABLE,
            schema.CREATE_PROVIDER_BENCHMARKS_INDEXES,
        ),
    ),
    Migration(
        version=16,
        name="create_provider_health_checks_table",
        statements=(
            schema.CREATE_PROVIDER_HEALTH_CHECKS_TABLE,
            schema.CREATE_PROVIDER_HEALTH_CHECKS_INDEXES,
        ),
    ),
)


class MigrationRunner:
    def apply(self, connection: Connection) -> None:
        connection.executescript(schema.CREATE_SCHEMA_MIGRATIONS)
        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for migration in MIGRATIONS:
            if migration.version in applied:
                continue
            for statement in migration.statements:
                connection.executescript(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, time.time()),
            )
