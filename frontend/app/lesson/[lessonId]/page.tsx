export default function LessonPage({ params }: { params: { lessonId: string } }) {
    return (
        <main className="min-h-screen bg-gray-950 flex items-center justify-center">
            <div className="text-white text-center">
                <h1 className="text-2xl font-bold mb-2">Lesson</h1>
                <p className="text-gray-400">ID: {params.lessonId}</p>
            </div>
        </main>
    )
}
