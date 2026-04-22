import json
import re
from groq import Groq
from config import config
from models import ProcessedKnowledge, DocChunk

client = Groq(api_key=config.GROQ_API_KEY)


def chunk_text(text: str) -> list[str]:
    """Split raw docs into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + config.CHUNK_SIZE
        chunks.append(text[start:end])
        start += config.CHUNK_SIZE - config.CHUNK_OVERLAP
    return chunks


def extract_json(raw: str) -> dict:
    """
    Safely extract JSON from LLM response.
    Handles markdown code blocks, extra text, etc.
    """
    # Remove markdown code blocks
    raw = re.sub(r"```json|```", "", raw).strip()

    # Find first { and last } — extract just the JSON object
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")

    return json.loads(raw[start:end])


def process_docs(raw_docs: str, topic_name: str) -> ProcessedKnowledge:
    """Chunk docs and extract key concepts via LLM."""

    # ── Step 1: Chunk the raw docs ────────────────────────────────────
    raw_chunks = chunk_text(raw_docs)
    doc_chunks = [
        DocChunk(chunk_id=i, content=c, topic_hint=topic_name)
        for i, c in enumerate(raw_chunks)
    ]

    # ── Step 2: Extract concepts via Groq ─────────────────────────────
    sample = raw_docs[:3000]  # only send first 3000 chars to LLM

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured learning information from documentation. "
                        "Output only valid JSON. No explanation, no markdown, just JSON."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
Analyze this documentation for "{topic_name}" and extract:

DOCUMENTATION:
{sample}

Return this exact JSON format:
{{
  "key_concepts": ["concept1", "concept2"],
  "suggested_modules": ["Module 1: Intro", "Module 2: Core Features"]
}}

Rules:
- key_concepts: 8-12 specific technical concepts found in the docs
- suggested_modules: 3-5 logical teaching modules in learning order
- Output ONLY the JSON object, nothing else
"""
                }
            ],
            max_tokens=1000,
            temperature=0.3,
        )

        raw     = response.choices[0].message.content.strip()
        extracted = extract_json(raw)

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse failed: {e} — using fallback")
        extracted = {
            "key_concepts":      [topic_name],
            "suggested_modules": [f"Module 1: Introduction to {topic_name}"]
        }
    except Exception as e:
        print(f"⚠️ Groq call failed: {e} — using fallback")
        extracted = {
            "key_concepts":      [topic_name],
            "suggested_modules": [f"Module 1: Introduction to {topic_name}"]
        }

    # ── Step 3: Return structured output ──────────────────────────────
    return ProcessedKnowledge(
        topic_name=topic_name,
        total_chunks=len(doc_chunks),
        chunks=doc_chunks,
        key_concepts=extracted.get("key_concepts", []),
        suggested_modules=extracted.get("suggested_modules", [])
    )