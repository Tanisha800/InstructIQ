// components/PipelineProgress.tsx
"use client"

import { useEffect, useRef } from "react"
import { CheckCircle, Circle, Loader2, XCircle } from "lucide-react"
import { PipelineEvent } from "@/lib/types"
import AgentStatusBadge from "./AgentStatusBadge"
import { cn, scoreToColor, scoreToBarColor } from "@/lib/utils"

interface Props {
    events: PipelineEvent[]
    currentEvent: string
    running: boolean
}

const PIPELINE_STEPS = [
    { key: "processing", label: "Knowledge Processor" },
    { key: "architecting", label: "Architect Agent" },
    { key: "generating", label: "Content Agent" },
    { key: "testing", label: "Simulated Student" },
    { key: "evaluating", label: "Evaluation Engine" },
    { key: "validated", label: "Validated" },
]

const STEP_ORDER = PIPELINE_STEPS.map(s => s.key)

function getStepStatus(stepKey: string, currentEvent: string, events: PipelineEvent[]) {
    const currentIdx = STEP_ORDER.indexOf(
        STEP_ORDER.find(k => currentEvent.includes(k) || currentEvent === k) ?? ""
    )
    const stepIdx = STEP_ORDER.indexOf(stepKey)

    const rewriting = events.some(e => e.event === "rewriting")

    if (currentEvent === "validated" || currentEvent === "complete") {
        return "done"
    }
    if (stepIdx < currentIdx) return "done"
    if (stepIdx === currentIdx) return "active"
    return "pending"
}

export default function PipelineProgress({ events, currentEvent, running }: Props) {
    const logRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight
        }
    }, [events])

    const evalEvents = events.filter(e => e.event === "evaluation_result")

    return (
        <div className="space-y-6 animate-fade-in">

            {/* Pipeline Steps */}
            <div className="card">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                    Pipeline Stages
                </h3>
                <div className="space-y-3">
                    {PIPELINE_STEPS.map((step) => {
                        const status = getStepStatus(step.key, currentEvent, events)
                        return (
                            <div key={step.key} className="flex items-center gap-3">
                                {status === "done" && <CheckCircle size={18} className="text-green-400 shrink-0" />}
                                {status === "active" && <Loader2 size={18} className="text-blue-400 animate-spin shrink-0" />}
                                {status === "pending" && <Circle size={18} className="text-gray-700 shrink-0" />}
                                <span className={cn(
                                    "text-sm font-medium",
                                    status === "done" ? "text-green-300" :
                                        status === "active" ? "text-blue-300" :
                                            "text-gray-600"
                                )}>
                                    {step.label}
                                </span>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* Score History */}
            {evalEvents.length > 0 && (
                <div className="card space-y-3">
                    <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                        Evaluation History
                    </h3>
                    {evalEvents.map((e, i) => (
                        <div key={i} className="space-y-1.5">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-gray-400">Attempt {e.iteration}</span>
                                <span className={cn("font-bold", scoreToColor(e.score || 0))}>
                                    {((e.score || 0) * 100).toFixed(1)}%
                                    {e.passed ? " ✓" : " ✗"}
                                </span>
                            </div>
                            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                <div
                                    className={cn("h-full rounded-full transition-all duration-700", scoreToBarColor(e.score || 0))}
                                    style={{ width: `${(e.score || 0) * 100}%` }}
                                />
                            </div>
                            {e.overall_feedback && (
                                <p className="text-xs text-gray-500 leading-relaxed">
                                    {e.overall_feedback}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Live Event Log */}
            <div className="card">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Live Agent Log
                </h3>
                <div
                    ref={logRef}
                    className="space-y-2 max-h-64 overflow-y-auto pr-1"
                >
                    {events.map((ev, i) => (
                        <div key={i} className="flex items-start gap-2 animate-fade-in">
                            <AgentStatusBadge event={ev.event} iteration={ev.iteration} />
                            {ev.message && (
                                <span className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                                    — {ev.message}
                                </span>
                            )}
                        </div>
                    ))}
                    {running && (
                        <div className="flex items-center gap-2 text-gray-600 text-xs">
                            <Loader2 size={12} className="animate-spin" />
                            Processing...
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}