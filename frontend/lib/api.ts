// lib/api.ts
import axios from "axios"

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const api = axios.create({ baseURL: BASE })

export async function getLesson(lessonId: string) {
    const res = await api.get(`/api/lesson/${lessonId}`)
    return res.data
}

export async function getLessonStatus(lessonId: string) {
    const res = await api.get(`/api/lesson/${lessonId}/status`)
    return res.data
}