import json
import re
import uuid
import google.generativeai as genai
from config import config
from models import (
    LessonBlueprint, LearningObjective, Module,
    Exercise, AssessmentCheckpoint, ProcessedKnowledge
)

genai.configure(api_key=config.GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a senior Instructional Designer with 20+ years of experience.
You design pedagogically rigorous lesson blueprints strictly following:

1. Gagne's Nine Events of Instruction:
   - Gain attention, Inform objectives, Stimulate recall, Present content,
     Provide guidance, Elicit performance, Give feedback, Assess, Enhance retention

2. Merrill's First Principles:
   - Problem-centered, Activation, Demonstration, Application, Integration

STRICT RULES — NEVER VIOLATE:
- Output ONLY a valid JSON object. No text before or after.
- No markdown fences (no ```json or ```).
- No explanations, no comments, no apologies.
- Every field in the schema is REQUIRED. Never skip a field.
- Never hallucinate concepts not present in the documentation.
- Never create generic or vague objectives like "understand the topic".
- Every objective MUST start with "Student will be able to..."
- Every exercise MUST be directly solvable using the provided documentation.
- assessment_checkpoints MUST test concepts actually covered in the docs.
- If you cannot generate valid JSON, output {} and nothing else.
"""


GUARDRAILS = """
GUARDRAIL CHECKLIST — verify before outputting:
[ ] All objectives start with "Student will be able to..."
[ ] All bloom_levels are one of: remember, understand, apply, analyze, evaluate, create
[ ] All difficulties are one of: beginner, intermediate, advanced
[ ] All question_types are one of: mcq, short_answer, code
[ ] MCQ questions have exactly 4 options
[ ] Non-MCQ questions have options set to null
[ ] No field is missing or null except options for non-MCQ
[ ] All IDs are unique (obj_1, obj_2 / mod_1, mod_2 / ex_1, ex_2 / cp_1, cp_2)
[ ] Concepts covered in modules match key concepts from the documentation
[ ] Exercises are specific and actionable, not vague
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


def validate_blueprint_data(data: dict, topic_name: str) -> dict:
    """
    Validate and auto-fix common LLM mistakes before
    passing to Pydantic — prevents crashes from minor errors.
    """

    # ── Fix objectives ─────────────────────────────────────────────
    valid_bloom = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
    for obj in data.get("objectives", []):
        # Force correct prefix
        if not obj.get("description", "").startswith("Student will be able to"):
            obj["description"] = "Student will be able to " + obj.get("description", "")
        # Fix invalid bloom level
        if obj.get("bloom_level", "").lower() not in valid_bloom:
            obj["bloom_level"] = "understand"

    # ── Fix exercises ──────────────────────────────────────────────
    valid_difficulty = {"beginner", "intermediate", "advanced"}
    for ex in data.get("exercises", []):
        if ex.get("difficulty", "").lower() not in valid_difficulty:
            ex["difficulty"] = "beginner"
        # Ensure expected_output is never empty
        if not ex.get("expected_output", "").strip():
            ex["expected_output"] = f"A working solution demonstrating {topic_name} concepts"

    # ── Fix assessment checkpoints ─────────────────────────────────
    valid_types = {"mcq", "short_answer", "code"}
    for cp in data.get("assessment_checkpoints", []):
        if cp.get("question_type", "").lower() not in valid_types:
            cp["question_type"] = "short_answer"
        # MCQ must have exactly 4 options
        if cp.get("question_type") == "mcq":
            if not cp.get("options") or len(cp.get("options", [])) != 4:
                cp["options"] = [
                    cp.get("correct_answer", "Option A"),
                    "Incorrect option B",
                    "Incorrect option C",
                    "Incorrect option D"
                ]
        else:
            # Non-MCQ must have null options
            cp["options"] = None

    # ── Fix modules ────────────────────────────────────────────────
    valid_gagne = {
        "Gain attention", "Inform objectives", "Stimulate recall",
        "Present content", "Provide guidance", "Elicit performance",
        "Give feedback", "Assess performance", "Enhance retention"
    }
    for mod in data.get("modules", []):
        if not mod.get("gagne_events"):
            mod["gagne_events"] = ["Present content", "Elicit performance", "Give feedback"]
        if not mod.get("merrill_principles"):
            mod["merrill_principles"] = ["Demonstration", "Application"]
        if not mod.get("concepts_covered"):
            mod["concepts_covered"] = [topic_name]

    return data


def build_blueprint(knowledge: ProcessedKnowledge, lesson_id: str) -> LessonBlueprint:

    concepts_text = "\n".join(f"  - {c}" for c in knowledge.key_concepts)
    modules_hint  = "\n".join(f"  - {m}" for m in knowledge.suggested_modules)
    chunks_text   = "\n\n".join(
        f"[Chunk {c.chunk_id}]:\n{c.content[:600]}"
        for c in knowledge.chunks[:6]
    )

    prompt = f"""
You are designing a complete lesson blueprint for: "{knowledge.topic_name}"

═══════════════════════════════════════════════
EXTRACTED KEY CONCEPTS (use these — do not invent others):
{concepts_text}

SUGGESTED MODULE STRUCTURE (follow this order):
{modules_hint}

DOCUMENTATION SAMPLE (base all content on this):
{chunks_text}
═══════════════════════════════════════════════

Generate a complete lesson blueprint matching this EXACT JSON schema:

{{
  "objectives": [
    {{
      "id": "obj_1",
      "description": "Student will be able to [specific measurable action]",
      "bloom_level": "apply"
    }}
  ],
  "modules": [
    {{
      "module_id": "mod_1",
      "title": "Specific Module Title",
      "concepts_covered": ["exact_concept_from_docs"],
      "gagne_events": ["Gain attention", "Present content", "Elicit performance"],
      "merrill_principles": ["Demonstration", "Application"]
    }}
  ],
  "exercises": [
    {{
      "exercise_id": "ex_1",
      "title": "Specific Exercise Title",
      "description": "Precise task the student must complete using {knowledge.topic_name}",
      "expected_output": "Exact description of what a correct solution looks like",
      "difficulty": "beginner"
    }}
  ],
  "assessment_checkpoints": [
    {{
      "checkpoint_id": "cp_1",
      "question": "Specific question testing a concept from the docs",
      "correct_answer": "The precise correct answer",
      "question_type": "mcq",
      "options": ["Correct answer", "Wrong option B", "Wrong option C", "Wrong option D"]
    }},
    {{
      "checkpoint_id": "cp_2",
      "question": "Specific short answer question",
      "correct_answer": "The precise correct answer",
      "question_type": "short_answer",
      "options": null
    }}
  ],
  "prerequisite_knowledge": ["specific prereq 1", "specific prereq 2"]
}}

QUANTITY REQUIREMENTS:
- objectives: exactly 4 (bloom levels: remember, understand, apply, analyze)
- modules: exactly {len(knowledge.suggested_modules)} (match suggested modules above)
- exercises: exactly 3 (one beginner, one intermediate, one advanced)
- assessment_checkpoints: exactly 5 (2 mcq, 2 short_answer, 1 code)
- prerequisite_knowledge: 2-4 specific prerequisites

{GUARDRAILS}
"""

    try:
        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=config.GROQ_MAX_TOKENS,
            )
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        data = extract_json(raw)

        # Auto-fix common LLM mistakes before Pydantic validation
        data = validate_blueprint_data(data, knowledge.topic_name)

        blueprint = LessonBlueprint(
            lesson_id=lesson_id,
            topic_name=knowledge.topic_name,
            objectives=[
                LearningObjective(**o) for o in data["objectives"]
            ],
            modules=[
                Module(**m) for m in data["modules"]
            ],
            exercises=[
                Exercise(**e) for e in data["exercises"]
            ],
            assessment_checkpoints=[
                AssessmentCheckpoint(**c)
                for c in data["assessment_checkpoints"]
            ],
            prerequisite_knowledge=data.get("prerequisite_knowledge", [])
        )

        return blueprint

    except json.JSONDecodeError as e:
        print(f"❌ Architect JSON parse error: {e}")
        raise ValueError(f"Architect Agent returned invalid JSON: {e}")

    except KeyError as e:
        print(f"❌ Architect missing required field: {e}")
        raise ValueError(f"Architect Agent response missing field: {e}")

    except Exception as e:
        print(f"❌ Architect Agent failed: {e}")
        raise