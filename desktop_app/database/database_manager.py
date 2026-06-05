from __future__ import annotations

from pathlib import Path

from desktop_app.database.connection import DatabaseConnection
from desktop_app.database.migrations import MigrationRunner


class DatabaseManager:
    def __init__(
        self,
        database_path: Path,
        migration_runner: MigrationRunner | None = None,
    ) -> None:
        self.database_path = database_path
        self.connection = DatabaseConnection(database_path)
        self.migration_runner = migration_runner or MigrationRunner()

    def initialize(self) -> None:
        with self.connection.connect() as connection:
            self.migration_runner.apply(connection)

