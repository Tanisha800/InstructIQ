import json
import re
from groq import Groq
from config import config
from models import FullLesson, StudentAttempt, StudentAnswer

client = Groq(api_key=config.GROQ_API_KEY)

# ── Isolated system prompt ─────────────────────────────────────────────────────
# CRITICAL: Student agent has ZERO access to source documentation
# This is the core differentiator from the PDF:
# "A separate LLM context with no privileged knowledge attempts to
#  read and complete the generated lesson — simulating a real first-time learner"

SYSTEM_PROMPT = """
You are a junior developer student attempting a technical lesson for the FIRST TIME.

YOUR CONSTRAINTS — NEVER VIOLATE:
- You have ONLY the lesson content below. Nothing else.
- You have ZERO access to external documentation, APIs, or prior knowledge.
- You cannot search the internet or recall training data about this topic.
- You must answer ONLY based on what the lesson explicitly taught you.
- If the lesson was unclear, your answer MUST reflect that confusion honestly.
- Do NOT guess correctly if the lesson didn't explain it — that defeats the purpose.
- Do NOT use knowledge you have from training — pretend this is a brand new topic.

YOUR PERSONA:
- You are motivated but genuinely confused by poor explanations.
- You can follow worked examples if they are clear and complete.
- You struggle when examples are missing, vague, or use unexplained terms.
- You answer confidently when the lesson was clear.
- You answer poorly or say "the lesson didn't explain this" when it wasn't.

OUTPUT RULES:
- Output ONLY valid JSON. No markdown fences. No explanation outside JSON.
- Be brutally honest about confusion — this feedback improves the lesson.
- If you cannot generate valid JSON, output {} and nothing else.
"""

GUARDRAILS = """
GUARDRAIL CHECKLIST before outputting:
[ ] Every checkpoint_id from the assessment is answered — none skipped
[ ] Every exercise_id from the exercises is attempted — none skipped
[ ] Answers reflect ONLY what the lesson content taught — no outside knowledge
[ ] If lesson was unclear → student_answer says exactly what was confusing
[ ] confidence is one of: low, medium, high — nothing else
[ ] notes field explains specific confusion — not just "it was unclear"
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


def build_lesson_text(lesson: FullLesson) -> str:
    """
    Format the lesson as clean readable text for the student.
    Mirrors exactly what a real student would see in the UI.
    """
    text = f"# {lesson.topic_name}\n\n"
    text += f"{lesson.introduction}\n\n"
    text += "─" * 50 + "\n\n"

    for section in lesson.sections:
        text += f"## {section.title}\n\n"
        text += f"{section.content}\n\n"

        if section.examples:
            text += "**Examples:**\n"
            for ex in section.examples:
                text += f"- {ex}\n"
            text += "\n"

        if section.key_takeaways:
            text += "**Key Takeaways:**\n"
            for kt in section.key_takeaways:
                text += f"✓ {kt}\n"
            text += "\n"

        text += "─" * 50 + "\n\n"

    text += f"## Summary\n{lesson.summary}\n"
    return text


def validate_attempt_data(data: dict, lesson: FullLesson) -> dict:
    """
    Ensure student attempted every checkpoint and exercise.
    Fill in honest confusion responses for any missed ones.
    """
    answered_ids = {a.get("checkpoint_id") for a in data.get("answers", [])}
    attempted_ids = {e.get("exercise_id") for e in data.get("exercise_attempts", [])}

    # Fill missing checkpoint answers
    for cp in lesson.assessment:
        if cp.checkpoint_id not in answered_ids:
            data["answers"].append({
                "checkpoint_id": cp.checkpoint_id,
                "question":      cp.question,
                "student_answer": "The lesson did not cover this clearly enough for me to answer."
            })

    # Fill missing exercise attempts
    for ex in lesson.exercises:
        if ex.exercise_id not in attempted_ids:
            data["exercise_attempts"].append({
                "exercise_id": ex.exercise_id,
                "title":       ex.title,
                "attempt":     "I was not sure how to approach this based on the lesson content.",
                "confidence":  "low",
                "notes":       "The lesson did not provide enough examples for me to attempt this."
            })

    # Fix invalid confidence values
    valid_confidence = {"low", "medium", "high"}
    for attempt in data.get("exercise_attempts", []):
        if attempt.get("confidence", "").lower() not in valid_confidence:
            attempt["confidence"] = "low"

    return data


def attempt_lesson(lesson: FullLesson, attempt_number: int) -> StudentAttempt:
    """
    Simulated student reads the lesson and attempts all assessments.
    Core of the self-validating feedback loop from the PDF.
    """

    lesson_text = build_lesson_text(lesson)

    # Build assessment questions (student sees questions but NOT correct answers)
    questions_json = json.dumps([
        {
            "checkpoint_id": cp.checkpoint_id,
            "question":      cp.question,
            "question_type": cp.question_type,
            # MCQ students see options — just like real UI
            "options":       cp.options if cp.question_type == "mcq" else None
        }
        for cp in lesson.assessment
    ], indent=2)

    # Build exercises
    exercises_json = json.dumps([
        {
            "exercise_id": ex.exercise_id,
            "title":       ex.title,
            "description": ex.description,
            "difficulty":  ex.difficulty
        }
        for ex in lesson.exercises
    ], indent=2)

    prompt = f"""
You just read the following lesson as a first-time student.
Your job is to answer the assessment and attempt the exercises
using ONLY what the lesson taught you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LESSON (this is ALL you know — no other knowledge allowed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lesson_text[:4500]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ASSESSMENT QUESTIONS (answer every single one):
{questions_json}

EXERCISES (attempt every single one):
{exercises_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT HONESTY RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- If the lesson explained something clearly → answer correctly and confidently
- If the lesson was vague or missing examples → say exactly what was confusing
- If you are unsure → say what part of the lesson left you uncertain
- Do NOT answer correctly if the lesson didn't teach it — that defeats the test
- Your confusion = direct feedback to improve the lesson

Respond with this EXACT JSON:
{{
  "answers": [
    {{
      "checkpoint_id": "cp_1",
      "question": "exact question text",
      "student_answer": "your honest answer based only on the lesson"
    }}
  ],
  "exercise_attempts": [
    {{
      "exercise_id": "ex_1",
      "title": "exercise title",
      "attempt": "your full attempt at solving the exercise",
      "confidence": "low/medium/high",
      "notes": "specific part of the lesson that was unclear, or 'lesson explained this well'"
    }}
  ]
}}

This is attempt number {attempt_number}.
Answer ALL {len(lesson.assessment)} questions and attempt ALL {len(lesson.exercises)} exercises.

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
            temperature=0.8,  # Higher = realistic student variance
        )

        raw  = response.choices[0].message.content.strip()
        data = extract_json(raw)

        # Ensure all checkpoints and exercises were attempted
        data = validate_attempt_data(data, lesson)

        attempt = StudentAttempt(
            lesson_id=lesson.lesson_id,
            attempt_number=attempt_number,
            answers=[StudentAnswer(**a) for a in data["answers"]],
            exercise_attempts=data["exercise_attempts"]
        )

        return attempt

    except json.JSONDecodeError as e:
        print(f"❌ Student Agent JSON parse error: {e}")
        raise ValueError(f"Student Agent returned invalid JSON: {e}")

    except KeyError as e:
        print(f"❌ Student Agent missing field: {e}")
        raise ValueError(f"Student Agent response missing field: {e}")

    except Exception as e:
        print(f"❌ Student Agent failed: {e}")
        raise