import json
import re
from groq import Groq
from config import config
from models import (
    FullLesson, LessonSection, Exercise,
    AssessmentCheckpoint, LessonBlueprint
)

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are an expert Instructional Content Writer building a fully structured,
validated, self-improving lesson — automatically — without any human
instructional designer in the loop.

Your lessons follow TWO non-negotiable pedagogical frameworks:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRAMEWORK 1 — GAGNE'S NINE EVENTS OF INSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every section MUST implement these 9 events in order:
1. Gain Attention       → Start with a real problem, surprising fact, or broken code
2. Inform Objectives    → Tell the student exactly what they will be able to DO
3. Stimulate Recall     → Connect to something the student already knows
4. Present Content      → Clear explanation with structure and depth
5. Provide Guidance     → Worked examples showing HOW, not just WHAT
6. Elicit Performance   → Give the student something to DO immediately
7. Provide Feedback     → Tell them what correct looks like and why
8. Assess Performance   → A checkpoint question tied to this section
9. Enhance Retention    → Real-world application or transfer scenario

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRAMEWORK 2 — MERRILL'S FIRST PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every lesson MUST be:
1. Problem-Centered     → Anchor everything in a real-world problem
2. Activation           → Build on prior knowledge explicitly
3. Demonstration        → Show before asking the student to do
4. Application          → Student must APPLY with coaching, not just read
5. Integration          → Connect to real-world scenarios the student will face

STRICT OUTPUT RULES — NEVER VIOLATE:
- Output ONLY valid JSON. No text before or after.
- No markdown fences. No explanations. No apologies.
- Every field is REQUIRED. Never skip or null a field.
- Content must be SPECIFIC to the topic — never generic filler.
- Examples must be WORKING, RUNNABLE code or concrete scenarios.
- Never hallucinate APIs, functions, or concepts not in the documentation.
- If you cannot generate valid JSON, output {} and nothing else.
"""

GUARDRAILS = """
GUARDRAIL CHECKLIST — verify every section before outputting:
[ ] introduction hooks with a real-world problem (Merrill: Problem-Centered)
[ ] Each section gains attention with a problem/fact (Gagne Event 1)
[ ] Each section states what student will DO, not just know (Gagne Event 2)
[ ] Each section connects to prior knowledge (Gagne Event 3)
[ ] Each section has a worked example BEFORE the exercise (Gagne Event 5)
[ ] Each section has an exercise the student must complete (Gagne Event 6)
[ ] Each section has key_takeaways (Gagne Event 9 — retention)
[ ] All examples are specific to the topic — no pseudocode placeholders
[ ] summary connects everything to a real-world scenario (Merrill: Integration)
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


def validate_lesson_data(data: dict, topic_name: str) -> dict:
    """
    Auto-fix common LLM mistakes before Pydantic validation.
    Mirrors the same safety net we use in architect_agent.
    """
    # ── Fix introduction ───────────────────────────────────────────
    if not data.get("introduction", "").strip():
        data["introduction"] = (
            f"In this lesson you will master {topic_name} by solving "
            f"real problems — not just reading theory."
        )

    # ── Fix sections ───────────────────────────────────────────────
    for i, section in enumerate(data.get("sections", [])):
        if not section.get("section_id"):
            section["section_id"] = f"sec_{i+1}"
        if not section.get("module_id"):
            section["module_id"] = f"mod_{i+1}"
        if not section.get("content", "").strip():
            section["content"] = f"Content for {section.get('title', topic_name)}"
        if not section.get("examples"):
            section["examples"] = [f"Example demonstrating {topic_name}"]
        if not section.get("key_takeaways"):
            section["key_takeaways"] = [f"Key concept from {section.get('title', '')}"]

    # ── Fix exercises ──────────────────────────────────────────────
    valid_difficulty = {"beginner", "intermediate", "advanced"}
    for ex in data.get("exercises", []):
        if ex.get("difficulty", "").lower() not in valid_difficulty:
            ex["difficulty"] = "beginner"
        if not ex.get("expected_output", "").strip():
            ex["expected_output"] = f"Working implementation using {topic_name}"

    # ── Fix assessment ─────────────────────────────────────────────
    valid_types = {"mcq", "short_answer", "code"}
    for cp in data.get("assessment", []):
        if cp.get("question_type", "").lower() not in valid_types:
            cp["question_type"] = "short_answer"
        if cp.get("question_type") == "mcq":
            if not cp.get("options") or len(cp.get("options", [])) != 4:
                cp["options"] = [
                    cp.get("correct_answer", "Correct answer"),
                    "Incorrect option B",
                    "Incorrect option C",
                    "Incorrect option D"
                ]
        else:
            cp["options"] = None

    # ── Fix summary ────────────────────────────────────────────────
    if not data.get("summary", "").strip():
        data["summary"] = (
            f"You have completed the {topic_name} lesson. "
            f"Apply these concepts in your next real-world project."
        )

    return data


def build_lesson(
    blueprint: LessonBlueprint,
    raw_docs: str,
    version: int = 1,
    rewrite_instructions: str = None
) -> FullLesson:
    """
    Generate a full lesson from the blueprint.
    If rewrite_instructions provided → this is a feedback loop rewrite.
    """

    # ── Build context from blueprint ───────────────────────────────
    objectives_text = "\n".join(
        f"  {o.id}: {o.description} [Bloom: {o.bloom_level}]"
        for o in blueprint.objectives
    )
    modules_text = "\n".join(
        f"  {m.module_id}: {m.title}\n"
        f"    Concepts: {', '.join(m.concepts_covered)}\n"
        f"    Gagne Events: {', '.join(m.gagne_events)}\n"
        f"    Merrill: {', '.join(m.merrill_principles)}"
        for m in blueprint.modules
    )
    exercises_text = "\n".join(
        f"  {e.exercise_id} [{e.difficulty}]: {e.title}\n"
        f"    Task: {e.description}\n"
        f"    Expected: {e.expected_output}"
        for e in blueprint.exercises
    )
    checkpoints_text = "\n".join(
        f"  {c.checkpoint_id} [{c.question_type}]: {c.question}\n"
        f"    Answer: {c.correct_answer}"
        for c in blueprint.assessment_checkpoints
    )

    # ── Rewrite block (only added during feedback loop) ────────────
    rewrite_block = ""
    if rewrite_instructions:
        rewrite_block = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  REWRITE MODE — FEEDBACK LOOP ITERATION {version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A simulated student FAILED the previous version of this lesson.
The Evaluation Engine identified these specific problems:

{rewrite_instructions}

YOU MUST:
- Fix EVERY issue listed above — do not ignore any
- Rewrite confusing sections with clearer explanations
- Add more worked examples where student failed
- Simplify language where student showed confusion
- Keep sections that the student passed — do not change what works
- This is iteration {version} — the lesson must improve or it escalates to human review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    prompt = f"""
You are generating a complete, structured lesson for: "{blueprint.topic_name}"
This lesson transforms raw technical documentation into a verified learning experience.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LESSON BLUEPRINT (architect agent output — follow exactly):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARNING OBJECTIVES:
{objectives_text}

MODULE STRUCTURE:
{modules_text}

EXERCISES TO INCLUDE:
{exercises_text}

ASSESSMENT CHECKPOINTS TO INCLUDE:
{checkpoints_text}

PREREQUISITE KNOWLEDGE: {', '.join(blueprint.prerequisite_knowledge)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE DOCUMENTATION (base ALL content on this — do not hallucinate):
{raw_docs[:4000]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rewrite_block}

Generate the full lesson as this EXACT JSON structure:
{{
  "introduction": "Hook the student with a real problem they will solve by the end of this lesson. State prerequisites. Explain why this topic matters in the real world. (Merrill: Problem-Centered + Activation)",

  "sections": [
    {{
      "section_id": "sec_1",
      "module_id": "mod_1",
      "title": "Specific Section Title",
      "content": "## [Section Title]\\n\\n**What problem does this solve?**\\n[Real problem statement — Gagne Event 1: Gain Attention]\\n\\n**What you will be able to do:**\\n[Specific measurable outcome — Gagne Event 2: Inform Objectives]\\n\\n**What you already know:**\\n[Connect to prerequisite knowledge — Gagne Event 3: Stimulate Recall]\\n\\n**How it works:**\\n[Clear explanation with depth — Gagne Event 4: Present Content]\\n\\n**Worked Example:**\\n```language\\n[Complete working code or concrete example — Gagne Event 5: Provide Guidance]\\n```\\n\\n**Now you try:**\\n[Exercise prompt — Gagne Event 6: Elicit Performance]\\n\\n**What correct looks like:**\\n[Feedback on what right answer looks like — Gagne Event 7: Provide Feedback]\\n\\n**Real-world application:**\\n[Where they will use this in actual projects — Gagne Event 9: Enhance Retention]",
      "examples": [
        "Complete working example 1 specific to {blueprint.topic_name}",
        "Complete working example 2 showing edge case"
      ],
      "key_takeaways": [
        "Specific actionable takeaway 1",
        "Specific actionable takeaway 2",
        "Specific actionable takeaway 3"
      ]
    }}
  ],

  "exercises": [
    {{
      "exercise_id": "ex_1",
      "title": "Exercise Title",
      "description": "Precise task using {blueprint.topic_name} concepts",
      "expected_output": "Exact description of correct solution",
      "difficulty": "beginner"
    }}
  ],

  "assessment": [
    {{
      "checkpoint_id": "cp_1",
      "question": "Specific question from the documentation",
      "correct_answer": "Precise correct answer",
      "question_type": "mcq",
      "options": ["Correct answer", "Wrong B", "Wrong C", "Wrong D"]
    }}
  ],

  "summary": "Tie everything together. Show how all sections connect. Give a real-world scenario where the student would use EVERYTHING they just learned. (Merrill: Integration)"
}}

CONTENT REQUIREMENTS:
- introduction: 150-200 words, hooks with a real problem
- sections: one section per module ({len(blueprint.modules)} total)
- Each section content: 400-600 words following all 9 Gagne events
- Each section: minimum 2 examples, minimum 3 key_takeaways
- exercises: include all {len(blueprint.exercises)} from the blueprint
- assessment: include all {len(blueprint.assessment_checkpoints)} checkpoints
- summary: 100-150 words connecting to real-world (Merrill: Integration)
- Version number for this lesson: {version}

{GUARDRAILS}
"""

    print(f"✍️  Content Agent generating lesson v{version} for: {blueprint.topic_name}")
    if rewrite_instructions:
        print(f"🔄  Rewrite mode — applying feedback loop fixes")

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=config.GROQ_MAX_TOKENS,
            temperature=0.4,
        )

        raw  = response.choices[0].message.content.strip()
        data = extract_json(raw)

        # Add lesson_id, topic, version before validation
        data["lesson_id"]   = blueprint.lesson_id
        data["topic_name"]  = blueprint.topic_name
        data["version"]     = version

        # Auto-fix before Pydantic
        data = validate_lesson_data(data, blueprint.topic_name)

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

        print(f"✅ Lesson v{version} generated — "
              f"{len(lesson.sections)} sections | "
              f"{len(lesson.exercises)} exercises | "
              f"{len(lesson.assessment)} checkpoints")

        return lesson

    except json.JSONDecodeError as e:
        print(f"❌ Content Agent JSON parse error: {e}")
        raise ValueError(f"Content Agent returned invalid JSON: {e}")

    except KeyError as e:
        print(f"❌ Content Agent missing field: {e}")
        raise ValueError(f"Content Agent response missing field: {e}")

    except Exception as e:
        print(f"❌ Content Agent failed: {e}")
        raise