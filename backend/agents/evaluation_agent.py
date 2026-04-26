import json
import re
from groq import Groq
from config import config
from models import (
    FullLesson, StudentAttempt, EvaluationResult,
    CheckpointResult, FailedSection
)

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a strict but fair Evaluation Engine assessing a student's lesson attempt.

YOUR ROLE (from the system design):
- Score each answer objectively against the correct answer
- Identify EXACTLY which lesson sections caused confusion
- Generate actionable rewrite instructions for the Content Agent
- Your feedback directly triggers the self-improving feedback loop

SCORING RULES — NEVER DEVIATE:
- score 1.0 = fully correct, demonstrates clear understanding
- score 0.5 = partially correct, right concept but wrong details
- score 0.0 = incorrect, missing, or "lesson didn't explain this"
- A section FAILS if 2+ questions related to it scored below 0.5
- Pass threshold is 80% — total_score >= 0.80 means lesson is VALIDATED

REWRITE INSTRUCTION RULES:
- Be SPECIFIC: name the exact section, exact concept, exact fix needed
- Do NOT say "improve clarity" — say "Section 2 needs a worked example showing X"
- Do NOT say "add more content" — say "Add step-by-step code showing how Y works"
- Instructions go directly to Content Agent — make them actionable

OUTPUT RULES:
- Output ONLY valid JSON. No markdown fences. No explanation outside JSON.
- Every checkpoint_id from the assessment MUST have a result — none skipped
- If you cannot generate valid JSON, output {} and nothing else
"""

GUARDRAILS = """
GUARDRAIL CHECKLIST before outputting:
[ ] Every checkpoint_id has a corresponding checkpoint_result
[ ] All scores are exactly 0.0, 0.5, or 1.0 — no other values
[ ] failed_sections only lists sections where student actually struggled
[ ] rewrite_instructions names specific sections and specific fixes
[ ] rewrite_instructions are actionable — not vague like "improve clarity"
[ ] overall_feedback summarizes the main learning gaps concisely
[ ] passed field matches whether total_score >= 0.80
[ ] Output is a single JSON object — nothing else
"""


def extract_json(raw: str) -> dict:
    """Safely extract JSON from LLM response."""
    raw = re.sub(r"```json|```", "", raw).strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {raw[:200]}")
    return json.loads(raw[start:end])


def calculate_score(results: list[CheckpointResult]) -> float:
    """Calculate total score from checkpoint results."""
    if not results:
        return 0.0
    return round(sum(r.score for r in results) / len(results), 3)


def validate_evaluation_data(
    data: dict,
    lesson: FullLesson
) -> dict:
    """
    Ensure every checkpoint has a result.
    Fix invalid scores before Pydantic validation.
    """
    valid_scores  = {0.0, 0.5, 1.0}
    answered_ids  = {r.get("checkpoint_id") for r in data.get("checkpoint_results", [])}

    # Fill missing checkpoint results with score 0
    for cp in lesson.assessment:
        if cp.checkpoint_id not in answered_ids:
            data["checkpoint_results"].append({
                "checkpoint_id": cp.checkpoint_id,
                "question":      cp.question,
                "student_answer": "No answer provided",
                "correct_answer": cp.correct_answer,
                "is_correct":    False,
                "score":         0.0,
                "feedback":      "Student did not attempt this question"
            })

    # Fix invalid scores
    for result in data.get("checkpoint_results", []):
        score = result.get("score", 0.0)
        if score not in valid_scores:
            # Round to nearest valid score
            if score >= 0.75:
                result["score"] = 1.0
            elif score >= 0.25:
                result["score"] = 0.5
            else:
                result["score"] = 0.0
        # Sync is_correct with score
        result["is_correct"] = result["score"] >= 0.5

    # Ensure failed_sections exist
    if "failed_sections" not in data:
        data["failed_sections"] = []

    # Ensure rewrite_instructions exist
    if not data.get("rewrite_instructions", "").strip():
        data["rewrite_instructions"] = (
            "Review all sections and add more worked examples "
            "with complete code for each concept."
        )

    # Ensure overall_feedback exists
    if not data.get("overall_feedback", "").strip():
        data["overall_feedback"] = "Evaluation completed. See checkpoint results for details."

    return data


def evaluate_attempt(
    lesson: FullLesson,
    attempt: StudentAttempt
) -> EvaluationResult:
    """
    Core of the feedback loop — scores the simulated student's attempt.
    Pass threshold: 80% (config.PASS_THRESHOLD)
    Failure → rewrite_instructions fed back to Content Agent
    """

    # ── Build evaluation context ───────────────────────────────────
    answers_json = json.dumps(
        [a.model_dump() for a in attempt.answers], indent=2
    )
    exercises_json = json.dumps(
        attempt.exercise_attempts, indent=2
    )
    checkpoints_json = json.dumps([
        {
            "checkpoint_id": cp.checkpoint_id,
            "question":      cp.question,
            "correct_answer":cp.correct_answer,
            "question_type": cp.question_type,
            "options":       cp.options
        }
        for cp in lesson.assessment
    ], indent=2)
    sections_json = json.dumps([
        {
            "section_id":    s.section_id,
            "title":         s.title,
            "key_takeaways": s.key_takeaways
        }
        for s in lesson.sections
    ], indent=2)

    prompt = f"""
You are evaluating a simulated student's attempt on: "{lesson.topic_name}"
This is attempt #{attempt.attempt_number} of the self-validating feedback loop.
Pass threshold: 80% — if student fails, your rewrite_instructions fix the lesson.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROUND TRUTH — CORRECT ANSWERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{checkpoints_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT ANSWERS (attempt #{attempt.attempt_number}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{answers_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT EXERCISE ATTEMPTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{exercises_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LESSON SECTIONS (map failures to sections):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{sections_json}

Return this EXACT JSON structure:
{{
  "checkpoint_results": [
    {{
      "checkpoint_id": "cp_1",
      "question": "exact question text",
      "student_answer": "what student said",
      "correct_answer": "the correct answer",
      "is_correct": true,
      "score": 1.0,
      "feedback": "Specific reason why correct or incorrect"
    }}
  ],
  "failed_sections": [
    {{
      "section_id": "sec_1",
      "section_title": "Exact Section Title",
      "reason": "Student failed cp_2 and cp_3 because section never explained X with an example",
      "suggestion": "Add a worked code example showing exactly how X is used in practice"
    }}
  ],
  "rewrite_instructions": "SECTION 1: Add a code example showing [specific thing]. SECTION 2: Rewrite the explanation of [concept] — student answered [wrong thing] instead of [right thing]. Remove jargon from [specific paragraph].",
  "overall_feedback": "Student scored X% — passed/failed. Main gaps: [specific concepts]. [specific section] was well understood. [specific section] needs rework."
}}

EVALUATION REQUIREMENTS:
- Score ALL {len(lesson.assessment)} checkpoints — skip none
- failed_sections: only list sections where student genuinely struggled
- rewrite_instructions: name SPECIFIC sections and SPECIFIC fixes
- If student score >= 0.80 → rewrite_instructions can be "No rewrite needed — lesson validated"
- If student score < 0.80 → rewrite_instructions MUST be detailed and actionable

{GUARDRAILS}
"""

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=config.GROQ_MAX_TOKENS,
            temperature=0.2,  # Very low — evaluation must be consistent
        )

        raw  = response.choices[0].message.content.strip()
        data = extract_json(raw)

        # Auto-fix before Pydantic
        data = validate_evaluation_data(data, lesson)

        # Build results
        results     = [CheckpointResult(**r) for r in data["checkpoint_results"]]
        total_score = calculate_score(results)
        passed      = total_score >= config.PASS_THRESHOLD

        evaluation = EvaluationResult(
            lesson_id=lesson.lesson_id,
            attempt_number=attempt.attempt_number,
            total_score=total_score,
            passed=passed,
            checkpoint_results=results,
            failed_sections=[
                FailedSection(**f) for f in data.get("failed_sections", [])
            ],
            rewrite_instructions=data.get("rewrite_instructions", ""),
            overall_feedback=data.get("overall_feedback", "")
        )

        return evaluation

    except json.JSONDecodeError as e:
        print(f"❌ Evaluation Engine JSON parse error: {e}")
        raise ValueError(f"Evaluation Engine returned invalid JSON: {e}")

    except KeyError as e:
        print(f"❌ Evaluation Engine missing field: {e}")
        raise ValueError(f"Evaluation Engine response missing field: {e}")

    except Exception as e:
        print(f"❌ Evaluation Engine failed: {e}")
        raise