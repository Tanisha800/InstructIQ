import sqlite3
import json
from config import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # enforce foreign keys
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id       TEXT PRIMARY KEY,
            topic_name      TEXT NOT NULL,
            raw_docs        TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'processing',
            iteration       INTEGER DEFAULT 0,
            validated       INTEGER DEFAULT 0,
            error           TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blueprints (
            lesson_id       TEXT PRIMARY KEY,
            blueprint_json  TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
        );

        CREATE TABLE IF NOT EXISTS lesson_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id       TEXT NOT NULL,
            version         INTEGER NOT NULL,
            content_json    TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
        );

        CREATE TABLE IF NOT EXISTS student_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id       TEXT NOT NULL,
            attempt_number  INTEGER NOT NULL,
            attempt_json    TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id       TEXT NOT NULL,
            attempt_number  INTEGER NOT NULL,
            score           REAL NOT NULL,
            passed          INTEGER NOT NULL,
            evaluation_json TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")  # helpful on startup


# ── Lesson CRUD ───────────────────────────────────────────────────────

def create_lesson(lesson_id: str, topic_name: str, raw_docs: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO lessons (lesson_id, topic_name, raw_docs) VALUES (?, ?, ?)",
        (lesson_id, topic_name, raw_docs)
    )
    conn.commit()
    conn.close()


def update_lesson_status(lesson_id: str, status: str, iteration: int = None,
                          validated: bool = None, error: str = None):
    conn = get_connection()
    fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    values = [status]

    if iteration is not None:
        fields.append("iteration = ?")
        values.append(iteration)
    if validated is not None:
        fields.append("validated = ?")
        values.append(1 if validated else 0)
    if error is not None:
        fields.append("error = ?")
        values.append(error)

    values.append(lesson_id)
    conn.execute(f"UPDATE lessons SET {', '.join(fields)} WHERE lesson_id = ?", values)
    conn.commit()
    conn.close()


def save_blueprint(lesson_id: str, blueprint_json: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO blueprints (lesson_id, blueprint_json) VALUES (?, ?)",
        (lesson_id, blueprint_json)
    )
    conn.commit()
    conn.close()


def save_lesson_version(lesson_id: str, version: int, content_json: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO lesson_versions (lesson_id, version, content_json) VALUES (?, ?, ?)",
        (lesson_id, version, content_json)
    )
    conn.commit()
    conn.close()


def save_student_attempt(lesson_id: str, attempt_number: int, attempt_json: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO student_attempts (lesson_id, attempt_number, attempt_json) VALUES (?, ?, ?)",
        (lesson_id, attempt_number, attempt_json)
    )
    conn.commit()
    conn.close()


def save_evaluation(lesson_id: str, attempt_number: int,
                    score: float, passed: bool, evaluation_json: str):
    conn = get_connection()
    conn.execute(
        """INSERT INTO evaluations
           (lesson_id, attempt_number, score, passed, evaluation_json)
           VALUES (?, ?, ?, ?, ?)""",
        (lesson_id, attempt_number, score, 1 if passed else 0, evaluation_json)
    )
    conn.commit()
    conn.close()


def get_lesson(lesson_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_lesson_version(lesson_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT * FROM lesson_versions WHERE lesson_id = ?
           ORDER BY version DESC LIMIT 1""",
        (lesson_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_evaluations(lesson_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM evaluations WHERE lesson_id = ? ORDER BY attempt_number",
        (lesson_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── NEW: Get blueprint ─────────────────────────────────────────────────

def get_blueprint(lesson_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM blueprints WHERE lesson_id = ?", (lesson_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── NEW: Get all lesson versions (for diff viewer) ─────────────────────

def get_all_lesson_versions(lesson_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM lesson_versions WHERE lesson_id = ?
           ORDER BY version ASC""",
        (lesson_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── NEW: Delete lesson (cleanup) ───────────────────────────────────────

def delete_lesson(lesson_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM lessons WHERE lesson_id = ?", (lesson_id,))
    conn.commit()
    conn.close()