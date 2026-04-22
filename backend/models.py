from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class LessonStatus(str, Enum):
    PROCESSING    = "processing"
    ARCHITECTING  = "architecting"
    GENERATING    = "generating"
    TESTING       = "testing"
    EVALUATING    = "evaluating"
    REWRITING     = "rewriting"
    VALIDATED     = "validated"
    FAILED        = "failed"


# ── Request / Response ────────────────────────────────────────────────

class DocsInput(BaseModel):
    raw_docs: str = Field(..., min_length=100, description="Raw documentation text")
    topic_name: str = Field(..., description="Name of the topic/library being taught")

class LessonResponse(BaseModel):
    lesson_id: str
    status: LessonStatus
    message: str

# ── NEW: SSE Event model ──────────────────────────────────────────────

class SSEEvent(BaseModel):
    event: str                        # agent name e.g. "architect"
    status: str                       # "started" | "done" | "error"
    message: str
    data: Optional[dict] = None       # any extra payload

# ── Knowledge Processor Output ────────────────────────────────────────

class DocChunk(BaseModel):
    chunk_id: int
    content: str
    topic_hint: str = ""


class ProcessedKnowledge(BaseModel):
    topic_name: str
    total_chunks: int
    chunks: list[DocChunk]
    key_concepts: list[str]
    suggested_modules: list[str]


# ── Architect Agent Output ────────────────────────────────────────────

class LearningObjective(BaseModel):
    id: str
    description: str
    bloom_level: str          # remember, understand, apply, analyze, evaluate, create


class Exercise(BaseModel):
    exercise_id: str
    title: str
    description: str
    expected_output: str
    difficulty: str           # beginner, intermediate, advanced


class AssessmentCheckpoint(BaseModel):
    checkpoint_id: str
    question: str
    correct_answer: str
    question_type: str        # mcq, short_answer, code
    options: Optional[list[str]] = None  # NEW: for MCQ options


class Module(BaseModel):
    module_id: str
    title: str
    concepts_covered: list[str]
    gagne_events: list[str]
    merrill_principles: list[str]


class LessonBlueprint(BaseModel):
    lesson_id: str
    topic_name: str
    objectives: list[LearningObjective]
    modules: list[Module]
    exercises: list[Exercise]
    assessment_checkpoints: list[AssessmentCheckpoint]
    prerequisite_knowledge: list[str]


# ── Content Agent Output ──────────────────────────────────────────────

class LessonSection(BaseModel):
    section_id: str
    module_id: str
    title: str
    content: str              # markdown
    examples: list[str]
    key_takeaways: list[str]


class FullLesson(BaseModel):
    lesson_id: str
    topic_name: str
    introduction: str
    sections: list[LessonSection]
    exercises: list[Exercise]
    assessment: list[AssessmentCheckpoint]
    summary: str
    version: int = 1


# ── Student Agent Output ──────────────────────────────────────────────

class StudentAnswer(BaseModel):
    checkpoint_id: str
    question: str
    student_answer: str
    exercise_id: Optional[str] = None


class StudentAttempt(BaseModel):
    lesson_id: str
    attempt_number: int
    answers: list[StudentAnswer]
    exercise_attempts: list[dict]


# ── Evaluation Engine Output ──────────────────────────────────────────

class CheckpointResult(BaseModel):
    checkpoint_id: str
    question: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    score: float
    feedback: str


class FailedSection(BaseModel):
    section_id: str
    section_title: str
    reason: str
    suggestion: str


class EvaluationResult(BaseModel):
    lesson_id: str
    attempt_number: int
    total_score: float              # 0.0 to 1.0
    passed: bool
    checkpoint_results: list[CheckpointResult]
    failed_sections: list[FailedSection]
    rewrite_instructions: str
    overall_feedback: str


# ── Pipeline State ────────────────────────────────────────────────────

class PipelineState(BaseModel):
    lesson_id: str
    topic_name: str
    raw_docs: str
    status: LessonStatus = LessonStatus.PROCESSING
    iteration: int = 0
    processed_knowledge: Optional[ProcessedKnowledge] = None
    blueprint: Optional[LessonBlueprint] = None
    current_lesson: Optional[FullLesson] = None
    last_evaluation: Optional[EvaluationResult] = None
    validated: bool = False
    error: Optional[str] = None

    # NEW: track all versions for DiffViewer
    lesson_versions: list[FullLesson] = []

    # NEW: track all evaluations for MasteryScore
    evaluation_history: list[EvaluationResult] = []