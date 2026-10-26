"""SQLite stores numeric summaries only, never names, filenames or source text."""
from contextlib import closing
from pathlib import Path
import sqlite3

from .analysis import TextStats
from .parsing import ParsedResume

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "history.sqlite3"


class HistoryStore:
    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            file_type TEXT NOT NULL CHECK(file_type IN ('PDF', 'DOCX')),
            size_bytes INTEGER NOT NULL,
            pages INTEGER,
            resume_words INTEGER NOT NULL,
            resume_characters INTEGER NOT NULL,
            job_words INTEGER NOT NULL,
            job_characters INTEGER NOT NULL
        )""")
        connection.commit()
        return connection

    def save(self, resume: ParsedResume, stats: TextStats, job_stats: TextStats) -> int:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("""INSERT INTO analyses
                (file_type, size_bytes, pages, resume_words, resume_characters, job_words, job_characters)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (resume.file_type, resume.size_bytes, resume.pages,
                stats.words, stats.characters, job_stats.words, job_stats.characters))
            return cursor.lastrowid

    def recent(self, limit: int = 100) -> list[dict]:
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,))]

    def clear(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM analyses")
