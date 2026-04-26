import json
import re
from groq import Groq
from config import config
from models import FullLesson, StudentAttempt, StudentAnswer

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a student attempting a lesson. Answer questions based only on the lesson content. Output only valid JSON."""


def extract_json(raw: str) -> dict:
    raw = re.sub(r"```json|```", "", raw).strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found: {raw[:200]}")
    return json.loads(raw[start:end])


def attempt_lesson(lesson: FullLesson, attempt_number: int) -> StudentAttempt:

    # Very short lesson summary
    lesson_summary = f"Topic: {lesson.topic_name}\n"
    lesson_summary += f"Introduction: {lesson.introduction[:300]}\n"
    for s in lesson.sections[:2]:
        lesson_summary += f"\nSection: {s.title}\n{s.content[:200]}\n"

    # Just first 3 questions
    questions = []
    for cp in lesson.assessment[:3]:
        questions.append({
            "checkpoint_id": cp.checkpoint_id,
            "question": cp.question,
            "question_type": cp.question_type
        })

    prompt = f"""
You read this lesson:
{lesson_summary}

Answer these questions based on what you learned:
{json.dumps(questions, indent=2)}

Also attempt this exercise:
Title: {lesson.exercises[0].title if lesson.exercises else 'Practice exercise'}
Task: {lesson.exercises[0].description[:200] if lesson.exercises else 'Apply the concepts'}

Respond as JSON:
{{
  "answers": [
    {{
      "checkpoint_id": "cp_1",
      "question": "question text",
      "student_answer": "your answer"
    }}
  ],
  "exercise_attempts": [
    {{
      "exercise_id": "ex_1",
      "title": "exercise title",
      "attempt": "your attempt",
      "confidence": "medium",
      "notes": "what was clear or unclear"
    }}
  ]
}}

Output ONLY the JSON. No other text.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7,
    )

    raw  = response.choices[0].message.content.strip()
    data = extract_json(raw)

    # Fill missing answers
    existing_ids = {a["checkpoint_id"] for a in data.get("answers", [])}
    for cp in lesson.assessment:
        if cp.checkpoint_id not in existing_ids:
            data.setdefault("answers", []).append({
                "checkpoint_id": cp.checkpoint_id,
                "question": cp.question,
                "student_answer": "I was not sure about this topic."
            })

    return StudentAttempt(
        lesson_id=lesson.lesson_id,
        attempt_number=attempt_number,
        answers=[StudentAnswer(**a) for a in data["answers"]],
        exercise_attempts=data.get("exercise_attempts", [{
            "exercise_id": "ex_1",
            "title": "Exercise",
            "attempt": "Applied the concepts from the lesson",
            "confidence": "medium",
            "notes": "Lesson was clear"
        }])
    )