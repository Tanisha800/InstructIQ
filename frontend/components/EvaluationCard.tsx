// components/EvaluationCard.tsx
import { CheckCircle, XCircle, AlertTriangle, Lightbulb } from "lucide-react"
import { EvaluationResult } from "@/lib/types"
import { scoreToColor, scoreToBarColor, cn } from "@/lib/utils"

interface Props {
    evaluation: EvaluationResult
    showRewrite?: boolean
}

export default function EvaluationCard({ evaluation, showRewrite }: Props) {
    return (
        <div className="card space-y-5 animate-fade-in">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {evaluation.passed
                        ? <CheckCircle size={18} className="text-green-400" />
                        : <XCircle size={18} className="text-red-400" />
                    }
                    <h3 className="font-bold text-white">
                        Attempt {evaluation.attempt_number} — Evaluation
                    </h3>
                </div>
                <span className={cn("text-2xl font-black", scoreToColor(evaluation.total_score))}>
                    {(evaluation.total_score * 100).toFixed(1)}%
                </span>
            </div>

            {/* Score Bar */}
            <div>
                <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full transition-all duration-700", scoreToBarColor(evaluation.total_score))}
                        style={{ width: `${evaluation.total_score * 100}%` }}
                    />
                </div>
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0%</span>
                    <span className="text-gray-400">Pass threshold: 80%</span>
                    <span>100%</span>
                </div>
            </div>

            {/* Overall Feedback */}
            {evaluation.overall_feedback && (
                <p className="text-sm text-gray-400 leading-relaxed bg-gray-800/40 rounded-xl p-3">
                    {evaluation.overall_feedback}
                </p>
            )}

            {/* Failed Sections */}
            {evaluation.failed_sections.length > 0 && (
                <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle size={12} />
                        Failed Sections ({evaluation.failed_sections.length})
                    </h4>
                    {evaluation.failed_sections.map((fs, i) => (
                        <div key={i} className="bg-red-950/30 border border-red-900/40 rounded-xl p-3 space-y-1.5">
                            <p className="text-sm font-semibold text-red-300">{fs.section_title}</p>
                            <p className="text-xs text-gray-400">{fs.reason}</p>
                            <div className="flex items-start gap-1.5 text-xs text-yellow-300">
                                <Lightbulb size={12} className="shrink-0 mt-0.5" />
                                <span>{fs.suggestion}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Rewrite Instructions */}
            {showRewrite && evaluation.rewrite_instructions && (
                <div className="bg-amber-950/30 border border-amber-900/40 rounded-xl p-3">
                    <p className="text-xs font-semibold text-amber-400 mb-1">Rewrite Instructions</p>
                    <p className="text-xs text-gray-400 leading-relaxed">{evaluation.rewrite_instructions}</p>
                </div>
            )}
        </div>
    )
}