// components/DocUploader.tsx
"use client"

import { useState } from "react"
import { Upload, FileText, Zap, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
    onSubmit: (rawDocs: string, topicName: string) => void
    disabled?: boolean
}

const SAMPLE_DOCS = `# FastAPI Quick Reference

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+.

## Installation
pip install fastapi uvicorn

## Creating an App
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

## Path Parameters
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

## Request Body
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

@app.post("/items/")
def create_item(item: Item):
    return item

## Running the server
uvicorn main:app --reload

## Automatic Docs
FastAPI auto-generates docs at /docs (Swagger UI) and /redoc.

## Query Parameters
@app.get("/users/")
def read_users(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

## HTTP Methods
FastAPI supports GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD.

## Status Codes
from fastapi import status

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item

## Error Handling
from fastapi import HTTPException

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    return db[item_id]

## Dependency Injection
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()
`

export default function DocUploader({ onSubmit, disabled }: Props) {
    const [docs, setDocs] = useState("")
    const [topic, setTopic] = useState("")
    const [dragOver, setDragOver] = useState(false)

    const handleSubmit = () => {
        if (!docs.trim() || !topic.trim()) return
        onSubmit(docs.trim(), topic.trim())
    }

    const loadSample = () => {
        setDocs(SAMPLE_DOCS)
        setTopic("FastAPI Framework")
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
                    onChange={e => setTopic(e.target.value)}
                    placeholder="e.g. FastAPI, Redis, Stripe API..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3
                     text-white placeholder-gray-500 focus:outline-none
                     focus:border-blue-500 transition-colors"
                    disabled={disabled}
                />
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
                        onChange={e => setDocs(e.target.value)}
                        placeholder="Paste your raw documentation here...
            
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
                    <span className="text-xs text-gray-600">
                        {docs.length.toLocaleString()} characters
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
            </div>

            {/* Submit */}
            <button
                onClick={handleSubmit}
                disabled={disabled || !docs.trim() || !topic.trim()}
                className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-2"
            >
                <Zap size={20} />
                Generate Curriculum
            </button>
        </div>
    )
}