import json
import uuid
import sys
import os

# Add backend root to path so database.py is found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import AsyncGenerator
from config import config
from models import PipelineState, LessonStatus
from services.knowledge_processor import process_docs
from services.feedback_loop import run_feedback_loop
from agents import architect_agent, content_agent
import asyncio
import database

def _sse(event: str, message: str, **kwargs) -> dict:
    """Consistent SSE event builder — matches feedback_loop.py."""
    return {"event": event, "message": message, **kwargs}


async def run_pipeline(
    raw_docs: str,
    topic_name: str
) -> AsyncGenerator[dict, None]:
    """
    Master pipeline controller.
    Orchestrates all 9 stages from the PDF:

    Stage 1 → Knowledge Processor
    Stage 2 → Architect Agent
    Stage 3 → Content Agent (v1)
    Stage 4 → Feedback Loop (Student → Evaluate → Rewrite)
    Stage 5 → Validated lesson shipped to user

    Yields SSE events at every step → frontend shows live progress.
    """

    lesson_id = str(uuid.uuid4())[:8]

    state = PipelineState(
        lesson_id=lesson_id,
        topic_name=topic_name,
        raw_docs=raw_docs
    )

    # Create lesson record in DB immediately
    try:
        database.create_lesson(lesson_id, topic_name, raw_docs)
    except Exception as e:
        yield _sse("error", f"❌ Failed to create lesson in DB: {str(e)}",
                   lesson_id=lesson_id, fatal=True)
        return

    try:
        # ── Stage 1: Pipeline Started ──────────────────────────────
        yield _sse(
            "started",
            f"🚀 Pipeline started for '{topic_name}'",
            lesson_id=lesson_id,
            topic_name=topic_name
        )

        # ── Stage 2: Knowledge Processing ─────────────────────────
        state.status = LessonStatus.PROCESSING
        database.update_lesson_status(lesson_id, LessonStatus.PROCESSING)

        yield _sse(
            "processing",
            "🔍 Chunking and analyzing documentation..."
        )

        knowledge = await asyncio.to_thread(process_docs, raw_docs, topic_name)
        state.processed_knowledge = knowledge

        yield _sse(
            "knowledge_ready",
            f"📚 Extracted {len(knowledge.key_concepts)} concepts "
            f"across {knowledge.total_chunks} chunks",
            chunks=knowledge.total_chunks,
            concepts=knowledge.key_concepts,
            suggested_modules=knowledge.suggested_modules
        )

        # ── Stage 3: Architect Agent ───────────────────────────────
        state.status = LessonStatus.ARCHITECTING
        database.update_lesson_status(lesson_id, LessonStatus.ARCHITECTING)

        yield _sse(
            "architecting",
            "🏗️  Architect Agent building lesson blueprint..."
        )

        blueprint = await asyncio.to_thread(architect_agent.build_blueprint, knowledge, lesson_id)
        state.blueprint = blueprint

        # Save blueprint to DB
        try:
            database.save_blueprint(
                lesson_id,
                json.dumps(blueprint.model_dump(), default=str)
            )
        except Exception as e:
            print(f"⚠️  DB save blueprint failed: {e}")

        yield _sse(
            "blueprint_ready",
            f"📋 Blueprint ready — {len(blueprint.modules)} modules | "
            f"{len(blueprint.objectives)} objectives | "
            f"{len(blueprint.exercises)} exercises | "
            f"{len(blueprint.assessment_checkpoints)} checkpoints",
            objectives=len(blueprint.objectives),
            modules=len(blueprint.modules),
            exercises=len(blueprint.exercises),
            checkpoints=len(blueprint.assessment_checkpoints),
            blueprint=blueprint.model_dump()
        )

        # ── Stage 4: Content Agent (v1) ────────────────────────────
        state.status = LessonStatus.GENERATING
        database.update_lesson_status(lesson_id, LessonStatus.GENERATING)

        yield _sse(
            "generating",
            "✍️  Content Agent generating full lesson v1..."
        )

        # FIX: was generate_lesson → correct name is build_lesson
        lesson = await asyncio.to_thread(
            content_agent.build_lesson,
            blueprint,  # positional arguments
            raw_docs,
            1           # version
        )
        state.current_lesson = lesson
        state.lesson_versions.append(lesson)

        # Save v1 to DB
        try:
            database.save_lesson_version(
                lesson_id, 1,
                json.dumps(lesson.model_dump(), default=str)
            )
        except Exception as e:
            print(f"⚠️  DB save lesson v1 failed: {e}")

        yield _sse(
            "lesson_ready",
            f"📄 Lesson v1 generated — {len(lesson.sections)} sections | "
            f"{len(lesson.exercises)} exercises | "
            f"{len(lesson.assessment)} checkpoints",
            version=1,
            sections=len(lesson.sections),
            exercises=len(lesson.exercises),
            checkpoints=len(lesson.assessment)
        )

        # ── Stage 5: Feedback Loop ─────────────────────────────────
        state.status = LessonStatus.TESTING
        database.update_lesson_status(lesson_id, LessonStatus.TESTING)

        yield _sse(
            "feedback_loop_starting",
            f"🔄 Starting feedback loop — "
            f"pass threshold: {config.PASS_THRESHOLD * 100:.0f}% | "
            f"max iterations: {config.MAX_FEEDBACK_ITERATIONS}"
        )

        async for event in run_feedback_loop(state):
            yield event

        # ── Stage 6: Final Output ──────────────────────────────────
        if state.validated:
            final_score = (
                state.last_evaluation.total_score
                if state.last_evaluation else 1.0
            )

            yield _sse(
                "complete",
                f"🎉 Pipeline complete! Lesson validated in "
                f"{state.iteration} iteration(s) with score "
                f"{final_score * 100:.1f}%",
                lesson_id=lesson_id,
                lesson=state.current_lesson.model_dump(),
                total_iterations=state.iteration,
                total_versions=state.current_lesson.version,
                final_score=final_score,
                final_score_percent=round(final_score * 100, 1),
                # Send all versions for DiffViewer
                all_versions=[v.model_dump() for v in state.lesson_versions],
                # Send score history for MasteryScore
                evaluation_history=[
                    e.model_dump() for e in state.evaluation_history
                ]
            )

        else:
            # Escalated — send best lesson anyway
            best_score = (
                state.last_evaluation.total_score
                if state.last_evaluation else 0.0
            )

            yield _sse(
                "pipeline_failed",
                f"⚠️ Pipeline ended without validation after "
                f"{state.iteration} iteration(s). "
                f"Best score: {best_score * 100:.1f}%. "
                f"Manual review required.",
                lesson_id=lesson_id,
                total_iterations=state.iteration,
                best_score=best_score,
                best_score_percent=round(best_score * 100, 1),
                # Still give user the best lesson we have
                lesson=state.current_lesson.model_dump()
                if state.current_lesson else None
            )

    except Exception as e:
        # Catch-all for unexpected errors
        state.status = LessonStatus.FAILED

        try:
            database.update_lesson_status(
                lesson_id,
                LessonStatus.FAILED,
                error=str(e)
            )
        except Exception:
            pass

        print(f"❌ Pipeline fatal error: {e}")

        yield _sse(
            "error",
            f"❌ Pipeline error: {str(e)}",
            lesson_id=lesson_id,
            error=str(e),
            fatal=True
        )
