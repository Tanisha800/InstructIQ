// components/LessonViewer.tsx
"use client"

import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { BookOpen, Dumbbell, ClipboardCheck, ChevronRight } from "lucide-react"
import { FullLesson } from "@/lib/types"
import ExerciseCard from "./ExerciseCard"
import { cn } from "@/lib/utils"

type Tab = "lesson" | "exercises" | "assessment"

interface Props {
    lesson: FullLesson
    finalScore?: number | null
}

export default function LessonViewer({ lesson, finalScore }: Props) {
    const [activeTab, setActiveTab] = useState<Tab>("lesson")
    const [activeSection, setActiveSection] = useState(0)

    const tabs = [
        { id: "lesson", label: "Lesson", icon: BookOpen, count: lesson.sections.length },
        { id: "exercises", label: "Exercises", icon: Dumbbell, count: lesson.exercises.length },
        { id: "assessment", label: "Assessment", icon: ClipboardCheck, count: lesson.assessment.length },
    ] as const

    return (
        <div className="card space-y-6 animate-fade-in">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="badge bg-green-900 text-green-300">✓ Validated</span>
                        <span className="badge bg-gray-800 text-gray-400">v{lesson.version}</span>
                        {finalScore && (
                            <span className="badge bg-blue-900 text-blue-300">
                                {(finalScore * 100).toFixed(0)}% Score
                            </span>
                        )}
                    </div>
                    <h2 className="text-xl font-bold text-white">{lesson.topic_name}</h2>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-800/60 p-1 rounded-xl">
                {tabs.map(tab => {
                    const Icon = tab.icon
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as Tab)}
                            className={cn(
                                "flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all",
                                activeTab === tab.id
                                    ? "bg-blue-600 text-white shadow"
                                    : "text-gray-400 hover:text-gray-200"
                            )}
                        >
                            <Icon size={14} />
                            {tab.label}
                            <span className={cn(
                                "text-xs px-1.5 py-0.5 rounded-full",
                                activeTab === tab.id ? "bg-blue-500/50" : "bg-gray-700"
                            )}>
                                {tab.count}
                            </span>
                        </button>
                    )
                })}
            </div>

            {/* Tab Content */}
            {activeTab === "lesson" && (
                <div className="space-y-4">
                    {/* Introduction */}
                    <div className="bg-blue-950/30 border border-blue-900/30 rounded-xl p-4">
                        <p className="text-sm text-gray-300 leading-relaxed">{lesson.introduction}</p>
                    </div>

                    {/* Section Navigation */}
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        {lesson.sections.map((s, i) => (
                            <button
                                key={s.section_id}
                                onClick={() => setActiveSection(i)}
                                className={cn(
                                    "shrink-0 text-xs px-3 py-1.5 rounded-lg font-medium transition-all",
                                    activeSection === i
                                        ? "bg-blue-600 text-white"
                                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                                )}
                            >
                                {i + 1}. {s.title.length > 20 ? s.title.slice(0, 20) + "…" : s.title}
                            </button>
                        ))}
                    </div>

                    {/* Active Section */}
                    {lesson.sections[activeSection] && (
                        <div className="space-y-4 animate-fade-in">
                            <h3 className="text-lg font-bold text-white">
                                {lesson.sections[activeSection].title}
                            </h3>
                            <div className="markdown-content">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {lesson.sections[activeSection].content}
                                </ReactMarkdown>
                            </div>

                            {lesson.sections[activeSection].key_takeaways.length > 0 && (
                                <div className="bg-gray-800/40 rounded-xl p-4">
                                    <p className="text-xs font-semibold text-blue-400 mb-2 uppercase tracking-wider">
                                        Key Takeaways
                                    </p>
                                    <ul className="space-y-1">
                                        {lesson.sections[activeSection].key_takeaways.map((t, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                                                <ChevronRight size={14} className="text-blue-400 shrink-0 mt-0.5" />
                                                {t}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Section Navigation */}
                            <div className="flex justify-between pt-2">
                                <button
                                    onClick={() => setActiveSection(i => Math.max(0, i - 1))}
                                    disabled={activeSection === 0}
                                    className="text-sm text-gray-400 hover:text-gray-200 disabled:opacity-30 transition-colors"
                                >
                                    ← Previous
                                </button>
                                <span className="text-xs text-gray-600">
                                    {activeSection + 1} / {lesson.sections.length}
                                </span>
                                <button
                                    onClick={() => setActiveSection(i => Math.min(lesson.sections.length - 1, i + 1))}
                                    disabled={activeSection === lesson.sections.length - 1}
                                    className="text-sm text-gray-400 hover:text-gray-200 disabled:opacity-30 transition-colors"
                                >
                                    Next →
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Summary */}
                    <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/30">
                        <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Summary</p>
                        <p className="text-sm text-gray-400 leading-relaxed">{lesson.summary}</p>
                    </div>
                </div>
            )}

            {activeTab === "exercises" && (
                <div className="space-y-3">
                    {lesson.exercises.map(ex => (
                        <ExerciseCard key={ex.exercise_id} exercise={ex} />
                    ))}
                </div>
            )}

            {activeTab === "assessment" && (
                <div className="space-y-4">
                    {lesson.assessment.map((cp, i) => (
                        <div key={cp.checkpoint_id} className="bg-gray-800/40 rounded-xl p-4 space-y-2">
                            <div className="flex items-center gap-2">
                                <span className="badge bg-gray-700 text-gray-400 text-xs">Q{i + 1}</span>
                                <span className="badge bg-gray-800 text-gray-500 text-xs border border-gray-700">
                                    {cp.question_type}
                                </span>
                            </div>
                            <p className="text-sm font-medium text-white">{cp.question}</p>
                            <div className="bg-green-950/30 border border-green-900/30 rounded-lg p-3">
                                <p className="text-xs text-green-400 font-semibold mb-0.5">Answer</p>
                                <p className="text-xs text-gray-300 font-mono leading-relaxed">{cp.correct_answer}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}