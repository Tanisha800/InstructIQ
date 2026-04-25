import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Groq ──────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.7

    CORS_ORIGINS: list = ["*"]

    # ── Evaluation ────────────────────────────────────
    PASS_THRESHOLD: float = 0.80
    MAX_FEEDBACK_ITERATIONS: int = 3

    # ── Database ──────────────────────────────────────
    DB_PATH: str = "lessons.db"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lessons.db")

    # ── Knowledge Processor ───────────────────────────
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200

    # ── FastAPI ───────────────────────────────────────
    APP_TITLE: str = "InstructIQ API"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: list = ["http://localhost:3000"]  # Next.js frontend

    # ── SSE ───────────────────────────────────────────
    SSE_PING_INTERVAL: int = 15  # seconds between keep-alive pings

    # ── Validation ────────────────────────────────────
    def validate(self):
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing in .env file")
        return self

config = Config().validate()