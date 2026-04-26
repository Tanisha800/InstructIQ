import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Groq ──────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"

    # ── Gemini ────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ── AI Provider ───────────────────────────────────
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")  # "gemini" or "groq"

    # ── Token Settings ────────────────────────────────
    GROQ_MAX_TOKENS: int = 2000
    GROQ_TEMPERATURE: float = 0.7

    # ── Evaluation ────────────────────────────────────
    PASS_THRESHOLD: float = 0.30
    MAX_FEEDBACK_ITERATIONS: int = 1

    # ── Database ──────────────────────────────────────
    DB_PATH: str = "lessons.db"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lessons.db")

    # ── Knowledge Processor ───────────────────────────
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200

    # ── FastAPI ───────────────────────────────────────
    APP_TITLE: str = "InstructIQ API"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: list = ["*"]

    # ── SSE ───────────────────────────────────────────
    SSE_PING_INTERVAL: int = 15

    # ── Validation ────────────────────────────────────
    def validate(self):
        if self.AI_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing in .env file")
        if self.AI_PROVIDER == "groq" and not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing in .env file")
        return self

config = Config().validate()