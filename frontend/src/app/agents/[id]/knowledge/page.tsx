"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getAgent, getIngestionStatus, startIngestion } from "@/lib/api"

interface IngestionStatus {
  status: string
  pages_crawled: number
  chunks_stored: number
  sources: { title: string; url: string }[]
  started_at?: string
  completed_at?: string
}

interface Agent {
  id: string
  name: string
  website_url: string
}

export default function KnowledgePage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [crawling, setCrawling] = useState(false)

  useEffect(() => {
    Promise.all([getAgent(params.id), getIngestionStatus(params.id)]).then(([a, s]) => {
      setAgent(a)
      setStatus(s)
      setLoading(false)
      if (s?.status === "running" || s?.status === "queued") {
        pollStatus()
      }
    })
  }, [params.id])

  const pollStatus = () => {
    const interval = setInterval(async () => {
      const s = await getIngestionStatus(params.id)
      setStatus(s)
      if (s?.status === "completed" || s?.status === "failed") {
        clearInterval(interval)
        setCrawling(false)
      }
    }, 3000)
    return () => clearInterval(interval)
  }

  const handleStartCrawl = async () => {
    setCrawling(true)
    try {
      await startIngestion(params.id)
      pollStatus()
    } catch {
      setCrawling(false)
    }
  }

  if (loading) return <div className="space-y-8"><div className="h-40 bg-gray-100 animate-pulse border-2 border-gray-200" /><div className="h-40 bg-gray-100 animate-pulse border-2 border-gray-200" /></div>

  const isRunning = status?.status === "running" || status?.status === "queued" || crawling
  const isCompleted = status?.status === "completed"

  return (
    <div className="space-y-12">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-4xl font-black mb-2">Knowledge</h2>
          <p className="text-xl font-medium text-gray-600">What Kokkopi has learned about your business.</p>
        </div>
        {!isRunning && (
          <button
            onClick={handleStartCrawl}
            className="bg-kokkopi-blue text-kokkopi-white font-black px-6 py-3 uppercase tracking-widest hover:bg-kokkopi-black transition-colors"
          >
            {isCompleted ? "Re-crawl" : "Start crawl"}
          </button>
        )}
      </div>

      {isRunning && (
        <div className="bg-kokkopi-yellow border-4 border-kokkopi-black p-6 flex items-center gap-4">
          <div className="w-6 h-6 border-4 border-kokkopi-black border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <div>
            <p className="font-black text-xl">Crawling your website...</p>
            <p className="font-bold text-gray-700">This takes 1–5 minutes depending on website size.</p>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-1 space-y-6">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-4">
            <h3 className="text-xl font-black">Knowledge Summary</h3>
            <div className="flex justify-between items-center py-2 border-b-2 border-kokkopi-black/10">
              <span className="font-bold text-gray-600">Status</span>
              <span className={`font-black uppercase text-sm px-2 py-1 border-2 ${isCompleted ? "border-kokkopi-teal text-kokkopi-teal" : isRunning ? "border-kokkopi-yellow text-kokkopi-black bg-kokkopi-yellow" : "border-gray-400 text-gray-500"}`}>
                {status?.status || "Not started"}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b-2 border-kokkopi-black/10">
              <span className="font-bold text-gray-600">Pages crawled</span>
              <span className="font-black text-xl">{status?.pages_crawled ?? 0}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b-2 border-kokkopi-black/10">
              <span className="font-bold text-gray-600">Knowledge chunks</span>
              <span className="font-black text-xl">{status?.chunks_stored ?? 0}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="font-bold text-gray-600">Website</span>
              <a href={agent?.website_url} target="_blank" rel="noreferrer" className="font-bold text-kokkopi-blue hover:underline text-sm truncate max-w-[120px]">
                {agent?.website_url?.replace(/^https?:\/\//, "")}
              </a>
            </div>
          </div>

          {!status && (
            <div className="bg-kokkopi-black text-kokkopi-white p-6 space-y-2">
              <p className="font-black">Ready to start</p>
              <p className="text-gray-400 font-bold text-sm">Click &quot;Start crawl&quot; to let Kokkopi learn your business.</p>
            </div>
          )}
        </div>

        <div className="md:col-span-2">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 h-full">
            <h3 className="text-2xl font-black mb-6">Crawled pages</h3>
            {!status?.sources?.length ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400 font-bold gap-3">
                <span className="text-5xl">📄</span>
                <span>No pages crawled yet.</span>
              </div>
            ) : (
              <div className="space-y-3">
                {status.sources.map((src, i) => (
                  <div key={i} className="p-4 border-2 border-kokkopi-black/10 hover:border-kokkopi-blue transition-colors">
                    <p className="font-bold text-lg">{src.title || "Untitled page"}</p>
                    <a href={src.url} target="_blank" rel="noreferrer" className="text-kokkopi-blue hover:underline text-sm font-mono">{src.url}</a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {isCompleted && (
        <div className="bg-kokkopi-teal text-kokkopi-white p-6 border-4 border-kokkopi-black flex items-center justify-between">
          <div>
            <p className="font-black text-xl">Knowledge ready!</p>
            <p className="font-bold opacity-80">Your agent can now answer questions about your business.</p>
          </div>
          <a href={`/agents/${params.id}/test`} className="bg-kokkopi-white text-kokkopi-black font-black px-6 py-3 hover:bg-kokkopi-yellow transition-colors">
            Test it →
          </a>
        </div>
      )}
    </div>
  )
}
