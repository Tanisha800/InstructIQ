// components/ExerciseCard.tsx
import { Dumbbell, ChevronDown, ChevronUp } from "lucide-react"
import { useState } from "react"
import { Exercise } from "@/lib/types"
import { difficultyColor, cn } from "@/lib/utils"

interface Props { exercise: Exercise }

export default function ExerciseCard({ exercise }: Props) {
    const [open, setOpen] = useState(false)

    return (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-700/30 transition-colors"
            >
                <Dumbbell size={16} className="text-blue-400 shrink-0" />
                <span className="font-semibold text-white flex-1">{exercise.title}</span>
                <span className={cn("badge text-xs", difficultyColor(exercise.difficulty))}>
                    {exercise.difficulty}
                </span>
                {open
                    ? <ChevronUp size={16} className="text-gray-500" />
                    : <ChevronDown size={16} className="text-gray-500" />
                }
            </button>

            {open && (
                <div className="px-4 pb-4 space-y-3 animate-fade-in">
                    <p className="text-sm text-gray-300 leading-relaxed">{exercise.description}</p>
                    <div className="bg-gray-900/60 rounded-lg p-3">
                        <p className="text-xs font-semibold text-green-400 mb-1">Expected Output</p>
                        <p className="text-xs text-gray-400 font-mono leading-relaxed">{exercise.expected_output}</p>
                    </div>
                </div>
            )}
        </div>
    )
}