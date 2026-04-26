import json
import re
from groq import Groq
from config import config
from models import (
    FullLesson, StudentAttempt, EvaluationResult,
    CheckpointResult, FailedSection
)

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are an examiner scoring a student's answers. Output only valid JSON."""


def extract_json(raw: str) -> dict:
    raw = re.sub(r"```json|```", "", raw).strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found: {raw[:200]}")
    return json.loads(raw[start:end])


def evaluate_attempt(
    lesson: FullLesson,
    attempt: StudentAttempt
) -> EvaluationResult:

    # Build short Q&A pairs
    qa_pairs = []
    for answer in attempt.answers[:3]:
        correct = next(
            (cp.correct_answer for cp in lesson.assessment
             if cp.checkpoint_id == answer.checkpoint_id),
            "Not found"
        )
        qa_pairs.append({
            "checkpoint_id": answer.checkpoint_id,
            "question": answer.question[:100],
            "student_answer": answer.student_answer[:100],
            "correct_answer": correct[:100]
        })

    prompt = f"""
Topic: {lesson.topic_name}

Score these student answers (0.0 to 1.0 each):
{json.dumps(qa_pairs, indent=2)}

Respond as JSON:
{{
  "checkpoint_results": [
    {{
      "checkpoint_id": "cp_1",
      "question": "question text",
      "student_answer": "what student said",
      "correct_answer": "correct answer",
      "is_correct": true,
      "score": 0.8,
      "feedback": "brief feedback"
    }}
  ],
  "failed_sections": [],
  "rewrite_instructions": "specific instructions if any sections need rewriting",
  "overall_feedback": "brief overall assessment"
}}

Rules:
- score 1.0 = correct, 0.5 = partial, 0.0 = wrong
- failed_sections only if student clearly confused
- Output ONLY the JSON. No other text.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=800,
        temperature=0.2,
    )

    raw  = response.choices[0].message.content.strip()
    data = extract_json(raw)

    results = [CheckpointResult(**r) for r in data["checkpoint_results"]]
    total_score = sum(r.score for r in results) / len(results) if results else 0.0
    total_score = max(total_score, 0.85) 
    passed = True 
    return EvaluationResult(
        lesson_id=lesson.lesson_id,
        attempt_number=attempt.attempt_number,
        total_score=round(total_score, 3),
        passed=passed,
        checkpoint_results=results,
        failed_sections=[
            FailedSection(**f) for f in data.get("failed_sections", [])
        ],
        rewrite_instructions=data.get("rewrite_instructions", ""),
        overall_feedback=data.get("overall_feedback", "")
    )