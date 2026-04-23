import sys
import os

# Fix Python path — must be FIRST before any other imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from config import config
from models import DocsInput, LessonResponse, LessonStatus
from services.lesson_service import run_pipeline
import database
# ── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=config.APP_TITLE,
    description="Multi-agent AI system for autonomous curriculum generation",
    version=config.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB on startup
database.init_db()


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":  "ok",
        "service": config.APP_TITLE,
        "version": config.APP_VERSION,
        "model":   config.GROQ_MODEL
    }


# ── Main Pipeline Route ───────────────────────────────────────────────────────
@app.post("/api/generate")
async def generate_lesson(payload: DocsInput):
    """
    Start the full multi-agent pipeline.
    Returns a Server-Sent Events (SSE) stream of all agent events.

    Events emitted (in order):
      started → processing → knowledge_ready → architecting →
      blueprint_ready → generating → lesson_ready →
      feedback_loop_starting → student_testing → evaluating →
      evaluation_result → (rewriting → lesson_rewritten →) *loop*
      validated / escalated → complete / pipeline_failed
    """

    # Validate input before starting pipeline
    if not payload.raw_docs.strip():
        raise HTTPException(
            status_code=400,
            detail="raw_docs cannot be empty"
        )
    if not payload.topic_name.strip():
        raise HTTPException(
            status_code=400,
            detail="topic_name cannot be empty"
        )

    async def event_stream():
        try:
            async for event in run_pipeline(
                payload.raw_docs,
                payload.topic_name
            ):
                data = json.dumps(event, default=str)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.01)  # prevent buffer flooding

        except Exception as e:
            # Stream the error so frontend knows what happened
            error_event = json.dumps({
                "event":   "error",
                "message": f"Stream error: {str(e)}",
                "fatal":   True
            })
            yield f"data: {error_event}\n\n"

        finally:
            # Always send stream_end so frontend closes SSE connection
            yield 'data: {"event": "stream_end"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        }
    )


# ── Get Lesson ────────────────────────────────────────────────────────────────
@app.get("/api/lesson/{lesson_id}")
async def get_lesson(lesson_id: str):
    """
    Fetch complete lesson data including:
    - lesson metadata
    - latest content version
    - all evaluation history
    - all versions (for DiffViewer)
    """
    lesson = database.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Latest content version
    version = database.get_latest_lesson_version(lesson_id)

    # All evaluations for MasteryScore
    evaluations = database.get_all_evaluations(lesson_id)

    # All versions for DiffViewer
    all_versions = database.get_all_lesson_versions(lesson_id)

    return {
        "lesson":      lesson,
        "content":     json.loads(version["content_json"]) if version else None,
        "evaluations": [
            {
                **{k: v for k, v in e.items() if k != "evaluation_json"},
                "evaluation": json.loads(e["evaluation_json"])
            }
            for e in evaluations
        ],
        "all_versions": [
            {
                "version":  v["version"],
                "content":  json.loads(v["content_json"]),
                "created_at": v["created_at"]
            }
            for v in all_versions
        ]
    }


# ── Get Lesson Status ─────────────────────────────────────────────────────────
@app.get("/api/lesson/{lesson_id}/status")
async def get_status(lesson_id: str):
    """Poll lesson pipeline status — used by frontend during generation."""
    lesson = database.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "lesson_id": lesson_id,
        "status":    lesson["status"],
        "iteration": lesson["iteration"],
        "validated": bool(lesson["validated"]),
        "error":     lesson["error"]
    }


# ── Get Blueprint ─────────────────────────────────────────────────────────────
@app.get("/api/lesson/{lesson_id}/blueprint")
async def get_blueprint(lesson_id: str):
    """Fetch the architect agent's lesson blueprint."""
    blueprint = database.get_blueprint(lesson_id)
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    return {
        "lesson_id": lesson_id,
        "blueprint": json.loads(blueprint["blueprint_json"])
    }


# ── List All Lessons ──────────────────────────────────────────────────────────
@app.get("/api/lessons")
async def list_lessons():
    """
    List all lessons — useful for debugging and admin view.
    """
    conn = database.get_connection()
    rows = conn.execute(
        """SELECT lesson_id, topic_name, status, iteration,
                  validated, created_at, updated_at
           FROM lessons
           ORDER BY created_at DESC
           LIMIT 50"""
    ).fetchall()
    conn.close()

    return {
        "lessons": [dict(r) for r in rows],
        "total":   len(rows)
    }


# ── Delete Lesson ─────────────────────────────────────────────────────────────
@app.delete("/api/lesson/{lesson_id}")
async def delete_lesson(lesson_id: str):
    """Delete a lesson and all related data — useful for testing."""
    lesson = database.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    database.delete_lesson(lesson_id)
    return {"message": f"Lesson {lesson_id} deleted successfully"}