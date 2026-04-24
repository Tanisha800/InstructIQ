// lib/types.ts

export type LessonStatus =
    | "processing"
    | "architecting"
    | "generating"
    | "testing"
    | "evaluating"
    | "rewriting"
    | "validated"
    | "failed"

export interface LearningObjective {
    id: string
    description: string
    bloom_level: string
}

export interface Module {
    module_id: string
    title: string
    concepts_covered: string[]
    gagne_events: string[]
    merrill_principles: string[]
}

export interface Exercise {
    exercise_id: string
    title: string
    description: string
    expected_output: string
    difficulty: "beginner" | "intermediate" | "advanced"
}

export interface AssessmentCheckpoint {
    checkpoint_id: string
    question: string
    correct_answer: string
    question_type: "mcq" | "short_answer" | "code"
}

export interface LessonBlueprint {
    lesson_id: string
    topic_name: string
    objectives: LearningObjective[]
    modules: Module[]
    exercises: Exercise[]
    assessment_checkpoints: AssessmentCheckpoint[]
    prerequisite_knowledge: string[]
}

export interface LessonSection {
    section_id: string
    module_id: string
    title: string
    content: string
    examples: string[]
    key_takeaways: string[]
}

export interface FullLesson {
    lesson_id: string
    topic_name: string
    introduction: string
    sections: LessonSection[]
    exercises: Exercise[]
    assessment: AssessmentCheckpoint[]
    summary: string
    version: number
}

export interface CheckpointResult {
    checkpoint_id: string
    question: string
    student_answer: string
    correct_answer: string
    is_correct: boolean
    score: number
    feedback: string
}

export interface FailedSection {
    section_id: string
    section_title: string
    reason: string
    suggestion: string
}

export interface EvaluationResult {
    lesson_id: string
    attempt_number: number
    total_score: number
    passed: boolean
    checkpoint_results: CheckpointResult[]
    failed_sections: FailedSection[]
    rewrite_instructions: string
    overall_feedback: string
}

// SSE Pipeline Events
export interface PipelineEvent {
    event: string
    lesson_id?: string
    message?: string
    iteration?: number
    score?: number
    passed?: boolean
    version?: number
    chunks?: number
    concepts?: string[]
    modules?: string[]
    sections?: number
    objectives?: number
    exercises?: number
    checkpoints?: number
    blueprint?: LessonBlueprint
    lesson?: FullLesson
    failed_sections?: FailedSection[]
    overall_feedback?: string
    rewrite_instructions?: string
    total_iterations?: number
    final_score?: number
    error?: string
}