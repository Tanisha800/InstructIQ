import json
import re
from groq import Groq
from config import config
from models import (
    FullLesson, LessonSection, Exercise,
    AssessmentCheckpoint, LessonBlueprint
)

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a technical educator. Generate structured lesson content as valid JSON only.
No markdown fences. No text before or after JSON. Output only the JSON object."""


def extract_json(raw: str) -> dict:
    raw = re.sub(r"```json|```", "", raw).strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found: {raw[:200]}")
    return json.loads(raw[start:end])


def build_lesson(
    blueprint: LessonBlueprint,
    raw_docs: str,
    version: int = 1,
    rewrite_instructions: str = None
) -> FullLesson:

    rewrite_note = ""
    if rewrite_instructions:
        rewrite_note = f"REWRITE INSTRUCTIONS: {rewrite_instructions[:300]}"

    # Keep prompt very short
    prompt = f"""
Topic: "{blueprint.topic_name}"
Version: {version}
{rewrite_note}

Documentation (use as source):
{raw_docs[:800]}

Generate a lesson as JSON:
{{
  "introduction": "2 paragraph introduction to {blueprint.topic_name}",
  "sections": [
    {{
      "section_id": "sec_1",
      "module_id": "mod_1", 
      "title": "Getting Started with {blueprint.topic_name}",
      "content": "## Introduction\\n\\nExplain the core concept here with a code example.\\n\\n```python\\n# example code\\n```\\n\\nExplain what the code does.",
      "examples": ["Example 1", "Example 2"],
      "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"]
    }},
    {{
      "section_id": "sec_2",
      "module_id": "mod_2",
      "title": "Core Features of {blueprint.topic_name}",
      "content": "## Core Features\\n\\nExplain 2-3 main features with examples.",
      "examples": ["Feature example 1", "Feature example 2"],
      "key_takeaways": ["Feature takeaway 1", "Feature takeaway 2", "Feature takeaway 3"]
    }},
    {{
      "section_id": "sec_3",
      "module_id": "mod_3",
      "title": "Practical Application",
      "content": "## Practical Use\\n\\nShow a real-world use case with complete example.",
      "examples": ["Real world example 1", "Real world example 2"],
      "key_takeaways": ["Practical takeaway 1", "Practical takeaway 2", "Practical takeaway 3"]
    }}
  ],
  "exercises": [
    {{
      "exercise_id": "ex_1",
      "title": "Basic Exercise",
      "description": "Create a basic implementation using {blueprint.topic_name}",
      "expected_output": "Working implementation with correct output",
      "difficulty": "beginner"
    }},
    {{
      "exercise_id": "ex_2", 
      "title": "Intermediate Exercise",
      "description": "Build a more complex feature using {blueprint.topic_name}",
      "expected_output": "Complete working solution",
      "difficulty": "intermediate"
    }}
  ],
  "assessment": [
    {{
      "checkpoint_id": "cp_1",
      "question": "What is the main purpose of {blueprint.topic_name}?",
      "correct_answer": "Based on the documentation provided",
      "question_type": "short_answer",
      "options": null
    }},
    {{
      "checkpoint_id": "cp_2",
      "question": "How do you install and set up {blueprint.topic_name}?",
      "correct_answer": "Using the installation method from the docs",
      "question_type": "short_answer",
      "options": null
    }},
    {{
      "checkpoint_id": "cp_3",
      "question": "What is a key feature of {blueprint.topic_name}?",
      "correct_answer": "Core feature from the documentation",
      "question_type": "short_answer",
      "options": null
    }}
  ],
  "summary": "Summary of {blueprint.topic_name} covering all key concepts learned."
}}

Fill in the actual content based on the documentation. Keep each section content under 200 words.
Output ONLY the JSON. No other text.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=3000,
        temperature=0.3,
    )

    raw  = response.choices[0].message.content.strip()
    data = extract_json(raw)

    data["lesson_id"]  = blueprint.lesson_id
    data["topic_name"] = blueprint.topic_name
    data["version"]    = version

    # Fix options field
    for cp in data.get("assessment", []):
        if cp.get("question_type") != "mcq":
            cp["options"] = None

    lesson = FullLesson(
        lesson_id=data["lesson_id"],
        topic_name=data["topic_name"],
        introduction=data["introduction"],
        sections=[LessonSection(**s) for s in data["sections"]],
        exercises=[Exercise(**e) for e in data["exercises"]],
        assessment=[AssessmentCheckpoint(**c) for c in data["assessment"]],
        summary=data["summary"],
        version=version
    )

    return lesson