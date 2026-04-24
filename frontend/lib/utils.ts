// lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export function scoreToColor(score: number): string {
    if (score >= 0.85) return "text-green-400"
    if (score >= 0.70) return "text-yellow-400"
    return "text-red-400"
}

export function scoreToBarColor(score: number): string {
    if (score >= 0.85) return "bg-green-500"
    if (score >= 0.70) return "bg-yellow-500"
    return "bg-red-500"
}

export function bloomColor(level: string): string {
    const map: Record<string, string> = {
        remember: "bg-gray-700 text-gray-300",
        understand: "bg-blue-900 text-blue-300",
        apply: "bg-indigo-900 text-indigo-300",
        analyze: "bg-purple-900 text-purple-300",
        evaluate: "bg-pink-900 text-pink-300",
        create: "bg-orange-900 text-orange-300",
    }
    return map[level.toLowerCase()] ?? "bg-gray-700 text-gray-300"
}

export function difficultyColor(d: string): string {
    const map: Record<string, string> = {
        beginner: "bg-green-900 text-green-300",
        intermediate: "bg-yellow-900 text-yellow-300",
        advanced: "bg-red-900 text-red-300",
    }
    return map[d] ?? "bg-gray-700 text-gray-300"
}

export function statusLabel(status: string): string {
    const map: Record<string, string> = {
        processing: "Processing Docs",
        architecting: "Building Blueprint",
        generating: "Writing Lesson",
        testing: "Testing with Student",
        evaluating: "Evaluating Answers",
        rewriting: "Rewriting Lesson",
        validated: "Validated ✓",
        failed: "Needs Review",
    }
    return map[status] ?? status
}