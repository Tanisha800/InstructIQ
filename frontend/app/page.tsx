// app/page.tsx
"use client"

import { usePipeline } from "@/hooks/usePipeline"
import DocUploader from "@/components/DocUploader"
import PipelineProgress from "@/components/PipelineProgress"
import BlueprintCard from "@/components/BlueprintCard"
import EvaluationCard from "@/components/EvaluationCard"
import LessonViewer from "@/components/LessonViewer"
import { AlertTriangle, RotateCcw } from "lucide-react"

export default function Home() {
    const { state, start, reset } = usePipeline()

    const showUploader = !state.running && !state.lessonId
    const showPipeline = state.lessonId !== null
    const showLesson = state.finalLesson !== null

    return (
        <main className="min-h-screen bg-gray-950">
            <div className="max-w-6xl mx-auto px-4 py-12">

                {/* Landing / Upload */}
                {showUploader && (
                    <div className="max-w-2xl mx-auto">
                        <DocUploader onSubmit={start} disabled={state.running} />
                    </div>
                )}

                {/* Pipeline Running */}
                {showPipeline && !showLesson && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left: Progress */}
                        <div className="lg:col-span-1 space-y-6">
                            <PipelineProgress
                                events={state.events}
                                currentEvent={state.currentEvent}
                                running={state.running}
                            />
                        </div>

                        {/* Right: Blueprint + Evaluations */}
                        <div className="lg:col-span-2 space-y-6">
                            {state.blueprint && <BlueprintCard blueprint={state.blueprint} />}

                            {state.evaluations.map((ev, i) => (
                                <EvaluationCard
                                    key={i}
                                    evaluation={ev}
                                    showRewrite={!ev.passed && i === state.evaluations.length - 1}
                                />
                            ))}

                            {state.error && (
                                <div className="card border border-red-900/50 bg-red-950/20 space-y-2">
                                    <div className="flex items-center gap-2 text-red-400">
                                        <AlertTriangle size={16} />
                                        <span className="font-semibold">Pipeline Error</span>
                                    </div>
                                    <p className="text-sm text-gray-400">{state.error}</p>
                                    <button onClick={reset} className="btn-primary text-sm py-2 flex items-center gap-2">
                                        <RotateCcw size={14} />
                                        Start Over
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Final Validated Lesson */}
                {showLesson && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left: Summary */}
                        <div className="lg:col-span-1 space-y-6">
                            <PipelineProgress
                                events={state.events}
                                currentEvent="complete"
                                running={false}
                            />

                            {state.evaluations.map((ev, i) => (
                                <EvaluationCard key={i} evaluation={ev} />
                            ))}

                            <button
                                onClick={reset}
                                className="w-full flex items-center justify-center gap-2 py-3 px-4
                           bg-gray-800 hover:bg-gray-700 rounded-xl text-gray-300
                           text-sm font-medium transition-colors"
                            >
                                <RotateCcw size={14} />
                                Generate New Lesson
                            </button>
                        </div>

                        {/* Right: Full Lesson */}
                        <div className="lg:col-span-2">
                            <LessonViewer
                                lesson={state.finalLesson!}
                                finalScore={state.finalScore}
                            />
                        </div>
                    </div>
                )}
            </div>
        </main>
    )
}