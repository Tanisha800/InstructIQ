// components/BlueprintCard.tsx
import { Target, Layers, Dumbbell, ClipboardList } from "lucide-react"
import { LessonBlueprint } from "@/lib/types"
import { bloomColor } from "@/lib/utils"

interface Props { blueprint: LessonBlueprint }

export default function BlueprintCard({ blueprint }: Props) {
    return (
        <div className="card space-y-6 animate-fade-in">
            <div className="flex items-center gap-2">
                <Layers size={18} className="text-indigo-400" />
                <h2 className="font-bold text-white">Lesson Blueprint</h2>
                <span className="badge bg-indigo-900 text-indigo-300 ml-auto">
                    Architect Agent
                </span>
            </div>

            {/* Objectives */}
            <div className="space-y-2">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Target size={12} /> Learning Objectives
                </h3>
                <div className="space-y-2">
                    {blueprint.objectives.map(obj => (
                        <div key={obj.id} className="flex items-start gap-2">
                            <span className={`badge text-xs shrink-0 mt-0.5 ${bloomColor(obj.bloom_level)}`}>
                                {obj.bloom_level}
                            </span>
                            <p className="text-sm text-gray-300">{obj.description}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Modules */}
            <div className="space-y-2">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers size={12} /> Modules
                </h3>
                <div className="grid gap-2">
                    {blueprint.modules.map((mod, i) => (
                        <div key={mod.module_id} className="bg-gray-800/50 rounded-xl p-3">
                            <p className="text-sm font-semibold text-white">
                                {i + 1}. {mod.title}
                            </p>
                            <div className="flex flex-wrap gap-1 mt-1.5">
                                {mod.concepts_covered.map(c => (
                                    <span key={c} className="badge bg-gray-700 text-gray-300 text-xs">
                                        {c}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Prerequisites */}
            {blueprint.prerequisite_knowledge.length > 0 && (
                <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        Prerequisites
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                        {blueprint.prerequisite_knowledge.map(p => (
                            <span key={p} className="badge bg-gray-800 text-gray-400 border border-gray-700">
                                {p}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}