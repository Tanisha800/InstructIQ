// hooks/usePipeline.ts
"use client"

import { useState, useRef, useCallback } from "react"
import { PipelineEvent, LessonBlueprint, FullLesson, EvaluationResult } from "@/lib/types"

export interface PipelineState {
    running: boolean
    lessonId: string | null
    events: PipelineEvent[]
    currentEvent: string
    blueprint: LessonBlueprint | null
    currentLesson: FullLesson | null
    evaluations: EvaluationResult[]
    finalLesson: FullLesson | null
    finalScore: number | null
    totalIterations: number
    error: string | null
    validated: boolean
}

const initialState: PipelineState = {
    running: false,
    lessonId: null,
    events: [],
    currentEvent: "",
    blueprint: null,
    currentLesson: null,
    evaluations: [],
    finalLesson: null,
    finalScore: null,
    totalIterations: 0,
    error: null,
    validated: false,
}

export function usePipeline() {
    const [state, setState] = useState<PipelineState>(initialState)
    const abortRef = useRef<AbortController | null>(null)

    const pushEvent = (event: PipelineEvent) => {
        setState(prev => ({
            ...prev,
            events: [...prev.events, event],
            currentEvent: event.event,
        }))
    }

    const start = useCallback(async (rawDocs: string, topicName: string) => {
        setState({ ...initialState, running: true })

        abortRef.current = new AbortController()

        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/generate`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ raw_docs: rawDocs, topic_name: topicName }),
                    signal: abortRef.current.signal,
                }
            )

            const reader = response.body!.getReader()
            const decoder = new TextDecoder()

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const text = decoder.decode(value)
                const lines = text.split("\n")

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue
                    const jsonStr = line.slice(6).trim()
                    if (!jsonStr || jsonStr === "") continue

                    try {
                        const event: PipelineEvent = JSON.parse(jsonStr)

                        if (event.event === "stream_end") {
                            setState(prev => ({ ...prev, running: false }))
                            break
                        }

                        if (event.event === "ping") {
                            continue
                        }

                        pushEvent(event)

                        // Handle specific events
                        setState(prev => {
                            const next = { ...prev }

                            if (event.event === "started" && event.lesson_id) {
                                next.lessonId = event.lesson_id
                            }

                            if (event.event === "blueprint_ready" && event.blueprint) {
                                next.blueprint = event.blueprint
                            }

                            if (event.event === "lesson_ready" || event.event === "lesson_rewritten") {
                                // lesson content saved via version
                            }

                            if (event.event === "evaluation_result") {
                                const evalEntry: EvaluationResult = {
                                    lesson_id: prev.lessonId || "",
                                    attempt_number: event.iteration || 1,
                                    total_score: event.score || 0,
                                    passed: event.passed || false,
                                    checkpoint_results: [],
                                    failed_sections: event.failed_sections || [],
                                    rewrite_instructions: event.rewrite_instructions || "",
                                    overall_feedback: event.overall_feedback || "",
                                }
                                next.evaluations = [...prev.evaluations, evalEntry]
                            }

                            if (event.event === "validated") {
                                next.validated = true
                                next.finalScore = event.score || null
                                next.totalIterations = event.iteration || 1
                            }

                            if (event.event === "complete" && event.lesson) {
                                next.finalLesson = event.lesson
                                next.finalScore = event.final_score || null
                                next.totalIterations = event.total_iterations || 1
                                next.running = false
                            }

                            if (event.event === "error") {
                                const raw = event.error || "Unknown error"
                                // Friendly message for Groq rate limit errors
                                if (raw.includes("rate_limit_exceeded") || raw.includes("Rate limit")) {
                                    const match = raw.match(/try again in ([\d]+m[\d.]+s|[\d.]+s)/i)
                                    const retryIn = match ? ` Please wait ${match[1]} and try again.` : " Please wait a few minutes and try again."
                                    next.error = `⏳ Groq API rate limit reached (daily token limit).${retryIn}`
                                } else {
                                    next.error = raw
                                }
                                next.running = false
                            }

                            if (event.event === "escalated") {
                                next.error = "Max iterations reached. Lesson needs manual review."
                                next.running = false
                            }

                            return next
                        })
                    } catch {
                        // skip malformed JSON lines
                    }
                }
            }
        } catch (err: any) {
            if (err.name !== "AbortError") {
                setState(prev => ({ ...prev, error: err.message, running: false }))
            }
        }
    }, [])

    const stop = useCallback(() => {
        abortRef.current?.abort()
        setState(prev => ({ ...prev, running: false }))
    }, [])

    const reset = useCallback(() => {
        setState(initialState)
    }, [])

    return { state, start, stop, reset }
}