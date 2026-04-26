// components/DocUploader.tsx
"use client"

import { useState } from "react"
import { Upload, FileText, Zap, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
    onSubmit: (rawDocs: string, topicName: string) => void
    disabled?: boolean
}

const SAMPLE_DOCS = `# Newton's Laws of Motion

Sir Isaac Newton's three laws of motion describe the relationship between a physical object and the forces acting upon it. Understanding these laws is fundamental to classical mechanics.

## First Law: Inertia
An object at rest remains at rest, and an object in motion remains in motion at constant speed and in a straight line unless acted on by an unbalanced force. 
- Example: A soccer ball sitting on the ground won't move until someone kicks it.

## Second Law: Force and Acceleration
The acceleration of an object depends on the mass of the object and the amount of force applied. 
- Formula: Force = mass × acceleration (F = ma)
- Example: It takes more force to push a heavy car than a light bicycle to achieve the same speed.

## Third Law: Action and Reaction
Whenever one object exerts a force on a second object, the second object exerts an equal and opposite force on the first.
- Example: When you jump off a small boat, you push yourself forward towards the dock, and the boat moves backward away from the dock.
`

export default function DocUploader({ onSubmit, disabled }: Props) {
    const [docs, setDocs] = useState("")
    const [topic, setTopic] = useState("")
    const [dragOver, setDragOver] = useState(false)
    const [errors, setErrors] = useState<{ topic?: string; docs?: string }>({})

    const handleSubmit = () => {
        const newErrors: { topic?: string; docs?: string } = {}
        if (!topic.trim()) newErrors.topic = "Topic name is required."
        if (!docs.trim()) newErrors.docs = "Please paste some documentation content."
        else if (docs.trim().length < 100) newErrors.docs = `Content too short — need at least 100 characters (you have ${docs.trim().length}).`
        if (Object.keys(newErrors).length > 0) { setErrors(newErrors); return }
        setErrors({})
        onSubmit(docs.trim(), topic.trim())
    }

    const loadSample = () => {
        setDocs(SAMPLE_DOCS)
        setTopic("Newton's Laws of Motion")
        setErrors({})
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer.files[0]
        if (!file) return
        const reader = new FileReader()
        reader.onload = (ev) => setDocs(ev.target?.result as string)
        reader.readAsText(file)
        if (!topic) setTopic(file.name.replace(/\.[^/.]+$/, ""))
    }

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Header */}
            <div className="text-center space-y-2">
                <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-blue-400 text-sm font-medium mb-4">
                    <Zap size={14} />
                    Multi-Agent AI Curriculum Engine
                </div>
                <h1 className="text-4xl font-bold text-white">
                    Algorithmic Instructional Designer
                </h1>
                <p className="text-gray-400 text-lg max-w-xl mx-auto">
                    Paste any raw documentation. Our AI agents will transform it into a
                    verified, structured lesson — automatically.
                </p>
            </div>

            {/* Topic Input */}
            <div className="card space-y-2">
                <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                    <BookOpen size={14} />
                    Topic / Library Name
                </label>
                <input
                    type="text"
                    value={topic}
                    onChange={e => { setTopic(e.target.value); setErrors(p => ({ ...p, topic: undefined })) }}
                    placeholder="e.g. Newton's Laws, FastAPI, Redis..."
                    className={`w-full bg-gray-800 border rounded-xl px-4 py-3
                     text-white placeholder-gray-500 focus:outline-none transition-colors
                     ${errors.topic ? 'border-red-500 focus:border-red-400' : 'border-gray-700 focus:border-blue-500'}`}
                    disabled={disabled}
                />
                {errors.topic && <p className="text-xs text-red-400 flex items-center gap-1">⚠ {errors.topic}</p>}
            </div>

            {/* Docs Textarea with Drag & Drop */}
            <div className="card space-y-2">
                <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                    <FileText size={14} />
                    Raw Documentation
                </label>

                <div
                    className={cn(
                        "relative rounded-xl border-2 border-dashed transition-colors",
                        dragOver ? "border-blue-500 bg-blue-500/5" : "border-gray-700"
                    )}
                    onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                >
                    <textarea
                        value={docs}
                        onChange={e => { setDocs(e.target.value); setErrors(p => ({ ...p, docs: undefined })) }}
                        placeholder="Paste your raw documentation, notes, or textbook content here (min 100 characters)...

Example: Paste Wikipedia text, lecture notes, a README, or any written material about your topic.
Do NOT just type a question — paste actual content to learn from.

Or drag & drop a .txt / .md file"
                        rows={14}
                        disabled={disabled}
                        className="w-full bg-transparent px-4 py-3 text-gray-300
                       placeholder-gray-600 font-mono text-sm resize-none
                       focus:outline-none rounded-xl"
                    />
                    {dragOver && (
                        <div className="absolute inset-0 flex items-center justify-center
                            bg-blue-500/10 rounded-xl pointer-events-none">
                            <div className="text-blue-400 flex flex-col items-center gap-2">
                                <Upload size={32} />
                                <span className="font-medium">Drop to load</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-between pt-1">
                    <span className={`text-xs ${docs.trim().length > 0 && docs.trim().length < 100 ? 'text-amber-500' : docs.trim().length >= 100 ? 'text-green-500' : 'text-gray-600'}`}>
                        {docs.trim().length.toLocaleString()} / 100 min chars
                        {docs.trim().length >= 100 && ' ✓'}
                    </span>
                    <button
                        onClick={loadSample}
                        disabled={disabled}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors
                       disabled:opacity-50"
                    >
                        Load sample docs →
                    </button>
                </div>
                {errors.docs && <p className="text-xs text-red-400 flex items-center gap-1 pt-1">⚠ {errors.docs}</p>}
            </div>

            {/* Submit */}
            <button
                onClick={handleSubmit}
                disabled={disabled}
                className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-2"
            >
                <Zap size={20} />
                Generate Curriculum
            </button>
        </div>
    )
}