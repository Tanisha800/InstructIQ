import json
import sys
import os

# Add backend root to path so database.py is found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import AsyncGenerator
from config import config
from models import PipelineState, LessonStatus
from agents import content_agent, student_agent, evaluation_agent
import database


def _safe_dump(obj) -> str:
    """Safely serialize a Pydantic model to JSON string."""
    return json.dumps(obj.model_dump(), default=str)


def _sse(event: str, message: str, **kwargs) -> dict:
    """Helper to build consistent SSE event dicts."""
    return {"event": event, "message": message, **kwargs}


async def run_feedback_loop(
    state: PipelineState
) -> AsyncGenerator[dict, None]:
    """
    Core of the self-validating feedback loop from the PDF:

    LOOP:
      1. Simulated Student attempts the lesson
      2. Evaluation Engine scores the attempt
      3. If score >= 80% → VALIDATED → ship to user
      4. If score < 80%  → rewrite_instructions → Content Agent rewrites
      5. Repeat until pass or max iterations reached
      6. If max iterations hit → escalate for human review

    Yields SSE events at every step so frontend shows live progress.
    """

    previous_lesson_json = None  # for diff viewer

    while state.iteration < config.MAX_FEEDBACK_ITERATIONS:
        state.iteration += 1

        # ── Step 1: Simulated Student Attempts ────────────────────
        yield _sse(
            "student_testing",
            f"🎓 Simulated student reading and attempting lesson "
            f"(iteration {state.iteration}/{config.MAX_FEEDBACK_ITERATIONS})...",
            iteration=state.iteration,
            version=state.current_lesson.version
        )

        try:
            attempt = student_agent.attempt_lesson(
                state.current_lesson,
                state.iteration
            )
        except Exception as e:
            yield _sse(
                "error",
                f"❌ Student Agent failed: {str(e)}",
                iteration=state.iteration,
                fatal=False
            )
            continue

        # Save attempt to DB
        try:
            database.save_student_attempt(
                state.lesson_id,
                state.iteration,
                _safe_dump(attempt)
            )
        except Exception as e:
            print(f"⚠️  DB save student attempt failed: {e}")

        # ── Step 2: Evaluate the Attempt ──────────────────────────
        yield _sse(
            "evaluating",
            f"📊 Evaluation Engine scoring attempt #{state.iteration}...",
            iteration=state.iteration
        )

        try:
            evaluation = evaluation_agent.evaluate_attempt(
                state.current_lesson,
                attempt
            )
            state.last_evaluation = evaluation
            state.evaluation_history.append(evaluation)

        except Exception as e:
            yield _sse(
                "error",
                f"❌ Evaluation Engine failed: {str(e)}",
                iteration=state.iteration,
                fatal=False
            )
            continue

        # Save evaluation to DB
        try:
            database.save_evaluation(
                state.lesson_id,
                state.iteration,
                evaluation.total_score,
                evaluation.passed,
                _safe_dump(evaluation)
            )
            database.update_lesson_status(
                state.lesson_id,
                LessonStatus.EVALUATING,
                iteration=state.iteration
            )
        except Exception as e:
            print(f"⚠️  DB save evaluation failed: {e}")

        # Yield detailed evaluation result to frontend
        yield _sse(
            "evaluation_result",
            f"Score: {evaluation.total_score * 100:.1f}% | "
            f"{'✅ PASSED' if evaluation.passed else '❌ FAILED — rewriting...'}",
            iteration=state.iteration,
            score=evaluation.total_score,
            score_percent=round(evaluation.total_score * 100, 1),
            passed=evaluation.passed,
            threshold_percent=round(config.PASS_THRESHOLD * 100, 1),
            failed_sections=[f.model_dump() for f in evaluation.failed_sections],
            checkpoint_results=[r.model_dump() for r in evaluation.checkpoint_results],
            overall_feedback=evaluation.overall_feedback,
            rewrite_instructions=evaluation.rewrite_instructions
        )

        # ── Step 3: Check Pass Condition ──────────────────────────
        if evaluation.passed:
            state.validated = True
            state.status    = LessonStatus.VALIDATED

            try:
                database.update_lesson_status(
                    state.lesson_id,
                    LessonStatus.VALIDATED,
                    iteration=state.iteration,
                    validated=True
                )
            except Exception as e:
                print(f"⚠️  DB update validated status failed: {e}")

            yield _sse(
                "validated",
                f"✅ Lesson VALIDATED after {state.iteration} iteration(s)! "
                f"Score: {evaluation.total_score * 100:.1f}% — shipping to user...",
                iteration=state.iteration,
                score=evaluation.total_score,
                score_percent=round(evaluation.total_score * 100, 1),
                total_versions=state.current_lesson.version,
                lesson=state.current_lesson.model_dump()
            )
            return

        # ── Step 4: Check if Max Iterations Reached ───────────────
        if state.iteration >= config.MAX_FEEDBACK_ITERATIONS:
            break

        # ── Step 5: Rewrite the Lesson ────────────────────────────
        state.status = LessonStatus.REWRITING

        try:
            database.update_lesson_status(
                state.lesson_id,
                LessonStatus.REWRITING,
                iteration=state.iteration
            )
        except Exception as e:
            print(f"⚠️  DB update rewriting status failed: {e}")

        yield _sse(
            "rewriting",
            f"🔄 Rewriting lesson v{state.current_lesson.version} → "
            f"v{state.current_lesson.version + 1} based on failure analysis...",
            iteration=state.iteration,
            failed_sections=[f.model_dump() for f in evaluation.failed_sections],
            rewrite_instructions=evaluation.rewrite_instructions
        )

        # Save current lesson JSON for diff viewer before rewrite
        previous_lesson_json = _safe_dump(state.current_lesson)

        new_version = state.current_lesson.version + 1

        try:
            rewritten_lesson = content_agent.build_lesson(
                blueprint=state.blueprint,
                raw_docs=state.raw_docs,
                version=new_version,
                rewrite_instructions=evaluation.rewrite_instructions
            )
            state.current_lesson = rewritten_lesson
            state.lesson_versions.append(rewritten_lesson)

        except Exception as e:
            yield _sse(
                "error",
                f"❌ Content Agent rewrite failed: {str(e)}",
                iteration=state.iteration,
                fatal=False
            )
            continue

        # Save new version to DB
        try:
            database.save_lesson_version(
                state.lesson_id,
                new_version,
                _safe_dump(rewritten_lesson)
            )
        except Exception as e:
            print(f"⚠️  DB save lesson version failed: {e}")

        yield _sse(
            "lesson_rewritten",
            f"📝 Lesson rewritten to v{new_version}. "
            f"Re-testing with simulated student...",
            iteration=state.iteration,
            version=new_version,
            # Send both versions for DiffViewer.tsx
            previous_lesson=json.loads(previous_lesson_json) if previous_lesson_json else None,
            new_lesson=rewritten_lesson.model_dump()
        )

    # ── Max Iterations Reached Without Passing ────────────────────
    final_score = (
        state.last_evaluation.total_score
        if state.last_evaluation else 0.0
    )

    state.status = LessonStatus.FAILED

    try:
        database.update_lesson_status(
            state.lesson_id,
            LessonStatus.FAILED,
            iteration=state.iteration,
            error=f"Max {config.MAX_FEEDBACK_ITERATIONS} iterations reached. "
                  f"Best score: {final_score * 100:.1f}%"
        )
    except Exception as e:
        print(f"⚠️  DB update failed status failed: {e}")

    yield _sse(
        "escalated",
        f"⚠️ Max {config.MAX_FEEDBACK_ITERATIONS} iterations reached without passing. "
        f"Best score: {final_score * 100:.1f}% "
        f"(threshold: {config.PASS_THRESHOLD * 100:.0f}%). "
        f"Lesson flagged for human review.",
        iteration=state.iteration,
        score=final_score,
        score_percent=round(final_score * 100, 1),
        threshold_percent=round(config.PASS_THRESHOLD * 100, 1),
        # Still send best lesson so user isn't left empty handed
        lesson=state.current_lesson.model_dump() if state.current_lesson else None,
        evaluation_history=[e.model_dump() for e in state.evaluation_history]
    )