from __future__ import annotations

import time

from desktop_app.database.connection import DatabaseConnection


class SettingsRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def get(self, key: str, default: str = "") -> str:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set(self, key: str, value: str) -> None:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, time.time()),
            )

    def set_many(self, values: dict[str, str]) -> None:
        now = time.time()
        with self.connection.connect() as connection:
            connection.executemany(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                [(key, value, now) for key, value in values.items()],
            )

    def all(self) -> dict[str, str]:
        with self.connection.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

