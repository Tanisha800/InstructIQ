// components/AgentStatusBadge.tsx
import { Brain, PenLine, GraduationCap, ClipboardCheck, RefreshCw, CheckCircle, XCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
    event: string
    iteration?: number
}

const EVENT_CONFIG: Record<string, {
    icon: React.ElementType
    label: string
    color: string
    pulse: boolean
}> = {
    started: { icon: Loader2, label: "Pipeline Starting", color: "text-blue-400", pulse: true },
    processing: { icon: Brain, label: "Processing Docs", color: "text-purple-400", pulse: true },
    knowledge_ready: { icon: Brain, label: "Knowledge Extracted", color: "text-purple-300", pulse: false },
    architecting: { icon: Brain, label: "Architect Agent", color: "text-indigo-400", pulse: true },
    blueprint_ready: { icon: Brain, label: "Blueprint Ready", color: "text-indigo-300", pulse: false },
    generating: { icon: PenLine, label: "Content Agent", color: "text-blue-400", pulse: true },
    lesson_ready: { icon: PenLine, label: "Lesson Generated", color: "text-blue-300", pulse: false },
    student_testing: { icon: GraduationCap, label: "Student Agent Testing", color: "text-yellow-400", pulse: true },
    evaluating: { icon: ClipboardCheck, label: "Evaluation Engine", color: "text-orange-400", pulse: true },
    evaluation_result: { icon: ClipboardCheck, label: "Evaluated", color: "text-orange-300", pulse: false },
    rewriting: { icon: RefreshCw, label: "Rewriting Lesson", color: "text-amber-400", pulse: true },
    lesson_rewritten: { icon: RefreshCw, label: "Lesson Rewritten", color: "text-amber-300", pulse: false },
    validated: { icon: CheckCircle, label: "Validated", color: "text-green-400", pulse: false },
    complete: { icon: CheckCircle, label: "Complete", color: "text-green-400", pulse: false },
    error: { icon: XCircle, label: "Error", color: "text-red-400", pulse: false },
    escalated: { icon: XCircle, label: "Needs Review", color: "text-red-400", pulse: false },
}

export default function AgentStatusBadge({ event, iteration }: Props) {
    const cfg = EVENT_CONFIG[event] ?? {
        icon: Loader2, label: event, color: "text-gray-400", pulse: false
    }
    const Icon = cfg.icon

    return (
        <div className={cn("flex items-center gap-2", cfg.color)}>
            <Icon
                size={16}
                className={cn(cfg.pulse && "animate-spin")}
                style={cfg.pulse && cfg.icon !== Loader2 ? { animation: "pulse 1.5s infinite" } : {}}
            />
            <span className="text-sm font-medium">
                {cfg.label}
                {iteration && iteration > 1 ? ` (Iteration ${iteration})` : ""}
            </span>
        </div>
    )
}