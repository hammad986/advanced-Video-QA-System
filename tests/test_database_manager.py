from __future__ import annotations

from desktop_app.database.database_manager import DatabaseManager


def test_database_manager_initializes_projects_schema(tmp_path) -> None:
    db_path = tmp_path / "app.db"
    manager = DatabaseManager(db_path)

    manager.initialize()

    with manager.connection.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        project_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        provider_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(provider_profiles)").fetchall()
        }
        video_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(videos)").fetchall()
        }
        transcript_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(transcripts)").fetchall()
        }
        segment_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(transcript_segments)").fetchall()
        }
        knowledge_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(knowledge_chunks)").fetchall()
        }
        topic_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(chunk_topics)").fetchall()
        }
        embedding_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(embeddings)").fetchall()
        }
        vector_index_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(vector_indexes)").fetchall()
        }
        retrieval_history_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(retrieval_history)").fetchall()
        }
        evidence_history_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(evidence_history)").fetchall()
        }
        chat_history_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(chat_history)").fetchall()
        }
        chat_sessions_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(chat_sessions)").fetchall()
        }
        chat_messages_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        compare_sessions_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(compare_sessions)").fetchall()
        }
        bookmarks_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(bookmarks)").fetchall()
        }
        highlights_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(highlights)").fetchall()
        }
        provider_usage_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(provider_usage)").fetchall()
        }
        provider_benchmarks_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(provider_benchmarks)").fetchall()
        }
        provider_health_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(provider_health_checks)").fetchall()
        }
        migrations = connection.execute("SELECT version FROM schema_migrations").fetchall()

    assert "projects" in tables
    assert "settings" in tables
    assert "provider_profiles" in tables
    assert "videos" in tables
    assert "transcripts" in tables
    assert "transcript_segments" in tables
    assert "knowledge_chunks" in tables
    assert "chunk_topics" in tables
    assert "embeddings" in tables
    assert "vector_indexes" in tables
    assert "retrieval_history" in tables
    assert "evidence_history" in tables
    assert "chat_history" in tables
    assert "chat_sessions" in tables
    assert "chat_messages" in tables
    assert "compare_sessions" in tables
    assert "bookmarks" in tables
    assert "highlights" in tables
    assert "provider_usage" in tables
    assert "provider_benchmarks" in tables
    assert "provider_health_checks" in tables
    assert "schema_migrations" in tables
    assert project_columns == {
        "id",
        "name",
        "description",
        "root_path",
        "status",
        "created_at",
        "updated_at",
        "archived_at",
    }
    assert provider_columns == {
        "id",
        "provider_name",
        "api_key_encrypted",
        "base_url",
        "model",
        "embedding_model",
        "enabled",
        "created_at",
        "updated_at",
    }
    assert video_columns == {
        "id",
        "project_id",
        "name",
        "file_path",
        "file_size",
        "duration",
        "fps",
        "width",
        "height",
        "thumbnail_path",
        "created_at",
        "updated_at",
    }
    assert transcript_columns == {
        "id",
        "video_id",
        "language",
        "model_name",
        "status",
        "created_at",
    }
    assert segment_columns == {
        "id",
        "transcript_id",
        "start_time",
        "end_time",
        "text",
        "confidence",
    }
    assert knowledge_columns == {
        "chunk_id",
        "transcript_id",
        "start_time",
        "end_time",
        "chunk_text",
        "topic_title",
        "confidence",
        "word_count",
        "created_at",
    }
    assert topic_columns == {
        "id",
        "chunk_id",
        "topic_title",
        "confidence",
    }
    assert embedding_columns == {
        "id",
        "chunk_id",
        "model_name",
        "dimension",
        "embedding_blob",
        "created_at",
    }
    assert vector_index_columns == {
        "id",
        "project_id",
        "embedding_model",
        "dimension",
        "index_path",
        "created_at",
        "updated_at",
    }
    assert retrieval_history_columns == {
        "id",
        "project_id",
        "query",
        "embedding_model",
        "top_k",
        "duration_ms",
        "created_at",
    }
    assert evidence_history_columns == {
        "id",
        "project_id",
        "query",
        "chunk_id",
        "rank",
        "similarity_score",
        "confidence_score",
        "created_at",
    }
    assert chat_history_columns == {
        "id",
        "project_id",
        "question",
        "answer",
        "citations_json",
        "provider",
        "duration_ms",
        "created_at",
        "updated_at",
    }
    assert chat_sessions_columns == {
        "id",
        "project_id",
        "title",
        "status",
        "created_at",
        "updated_at",
        "last_message_at",
        "deleted_at",
    }
    assert chat_messages_columns == {
        "id",
        "session_id",
        "project_id",
        "question",
        "answer",
        "citations_json",
        "provider",
        "provider_model",
        "duration_ms",
        "token_usage_json",
        "created_at",
    }
    assert compare_sessions_columns == {
        "id",
        "project_id",
        "session_name",
        "videos_json",
        "query",
        "result_json",
        "created_at",
    }
    assert bookmarks_columns == {
        "id",
        "project_id",
        "video_id",
        "chunk_id",
        "transcript_id",
        "segment_id",
        "bookmark_type",
        "title",
        "note",
        "timestamp",
        "source_text",
        "created_at",
        "updated_at",
    }
    assert highlights_columns == {
        "id",
        "project_id",
        "video_id",
        "transcript_id",
        "segment_id",
        "chunk_id",
        "highlighted_text",
        "color",
        "note",
        "timestamp",
        "created_at",
        "updated_at",
    }
    assert provider_usage_columns == {
        "id",
        "project_id",
        "provider",
        "model",
        "task_type",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "response_time_ms",
        "created_at",
    }
    assert provider_benchmarks_columns == {
        "id",
        "provider",
        "model",
        "task_type",
        "success",
        "latency_ms",
        "error_message",
        "created_at",
    }
    assert provider_health_columns == {
        "id",
        "provider",
        "profile_id",
        "status",
        "configured",
        "reachable",
        "authentication_valid",
        "model_available",
        "latency_ms",
        "message",
        "checked_at",
    }
    assert [row["version"] for row in migrations] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]


def test_database_manager_migrations_are_idempotent(tmp_path) -> None:
    db_path = tmp_path / "app.db"
    manager = DatabaseManager(db_path)

    manager.initialize()
    manager.initialize()

    with manager.connection.connect() as connection:
        count = connection.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()["n"]

    assert count == 16
