"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { getAgents, deleteAgent, getToken } from "@/lib/api"
import { Badge } from "@/components/ui/Badge"

interface Agent {
  id: string
  name: string
  type: string
  website_url: string
  status: string
  created_at: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      router.push("/login")
      return
    }
    getAgents().then(data => {
      setAgents(Array.isArray(data) ? data : data?.agents || [])
      setLoading(false)
    })
  }, [router])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete agent "${name}"? This cannot be undone.`)) return
    await deleteAgent(id)
    setAgents(prev => prev.filter(a => a.id !== id))
  }

  if (loading) {
    return (
      <div className="space-y-12">
        <div className="flex items-end justify-between">
          <h1 className="text-5xl font-black">Your agents</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-gray-100 border-2 border-gray-200 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-12">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-5xl font-black mb-2">Your agents</h1>
          <p className="text-xl font-medium text-gray-600">Control plane for your AI employees.</p>
        </div>
        <Link href="/agents/new">
          <button id="create_agent_btn" className="bg-kokkopi-red text-kokkopi-white font-black px-8 py-4 text-lg uppercase tracking-widest hover:bg-kokkopi-black transition-colors border-2 border-kokkopi-red hover:border-kokkopi-black">
            + Create agent
          </button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {agents.map(agent => (
          <div key={agent.id} className="bg-kokkopi-white border-4 border-kokkopi-black p-8 flex flex-col gap-6 hover:-translate-y-1 transition-transform">
            <div className="flex justify-between items-start">
              <h2 className="text-3xl font-black leading-tight">{agent.name}</h2>
              <Badge variant={agent.status === "active" ? "success" : "default"}>
                {agent.status || "Ready"}
              </Badge>
            </div>
            <div className="space-y-1">
              <p className="font-bold text-gray-700">{agent.type === "chat_voice" ? "Chat + Voice" : "Chat only"}</p>
              <p className="font-bold text-gray-500 font-mono text-sm truncate">{agent.website_url}</p>
            </div>
            <div className="mt-auto pt-4 flex gap-3 border-t-2 border-kokkopi-black">
              <Link href={`/agents/${agent.id}/knowledge`} className="flex-1">
                <button className="w-full border-2 border-kokkopi-black font-black py-2 px-4 hover:bg-kokkopi-yellow transition-colors text-sm">
                  Manage
                </button>
              </Link>
              <Link href={`/agents/${agent.id}/test`} className="flex-1">
                <button className="w-full bg-kokkopi-black text-kokkopi-white font-black py-2 px-4 hover:bg-kokkopi-teal transition-colors text-sm">
                  Test
                </button>
              </Link>
              <button
                onClick={() => handleDelete(agent.id, agent.name)}
                className="border-2 border-gray-300 font-black py-2 px-3 hover:border-kokkopi-red hover:text-kokkopi-red transition-colors text-sm"
              >
                ✕
              </button>
            </div>
          </div>
        ))}

        <Link href="/agents/new">
          <div className="bg-gray-50 border-4 border-dashed border-gray-300 p-8 flex flex-col gap-4 items-center justify-center text-center text-gray-400 hover:border-kokkopi-black hover:text-kokkopi-black hover:-translate-y-1 cursor-pointer transition-all h-full min-h-[200px]">
            <div className="text-5xl">🐣</div>
            <p className="font-black text-xl">New agent</p>
            <p className="font-medium text-sm">Add another AI employee</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
