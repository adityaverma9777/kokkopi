"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Navbar } from "@/components/layout/Navbar"
import { createAgent, getToken } from "@/lib/api"
import { useEffect } from "react"

export default function CreateAgentPage() {
  const router = useRouter()
  const [name, setName] = useState("My AI Agent")
  const [type, setType] = useState("chat_voice")
  const [websiteUrl, setWebsiteUrl] = useState("")
  const [sitemapUrl, setSitemapUrl] = useState("")
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!getToken()) router.push("/login")
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!consent) { setError("Please authorize website crawling to continue."); return }
    if (!websiteUrl) { setError("Website URL is required."); return }
    setError("")
    setLoading(true)
    try {
      const agent = await createAgent({ name, website_url: websiteUrl, sitemap_url: sitemapUrl || undefined, type })
      router.push(`/agents/${agent.id}/knowledge`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create agent")
    } finally {
      setLoading(false)
    }
  }

  const types = [
    { id: "chat", label: "Chat", icon: "💬", desc: "Text-only chat widget" },
    { id: "voice", label: "Voice", icon: "🎙️", desc: "Voice-only agent" },
    { id: "chat_voice", label: "Chat + Voice", icon: "🤖", desc: "Full conversational AI" },
  ]

  return (
    <div className="flex flex-col min-h-screen bg-kokkopi-white">
      <Navbar />
      <main className="flex-1 max-w-3xl w-full mx-auto p-8 pt-16">
        <h1 className="text-5xl font-black mb-2 text-center">Create your agent</h1>
        <p className="text-center text-gray-500 font-bold mb-10">Your AI employee will learn from your website automatically.</p>

        <form onSubmit={handleSubmit} className="bg-kokkopi-white border-4 border-kokkopi-black p-10 shadow-[8px_8px_0_0_#000407] space-y-10">
          <div className="space-y-3">
            <label className="block text-xl font-black uppercase tracking-widest">Agent name</label>
            <input
              id="agent_name"
              type="text"
              required
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold text-xl focus:outline-none focus:border-kokkopi-red"
            />
          </div>

          <div className="space-y-3">
            <label className="block text-xl font-black uppercase tracking-widest">Agent type</label>
            <div className="grid grid-cols-3 gap-4">
              {types.map(t => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setType(t.id)}
                  className={`border-4 p-5 flex flex-col items-center gap-2 transition-all ${type === t.id ? "border-kokkopi-black bg-kokkopi-yellow shadow-brand" : "border-kokkopi-black/20 hover:border-kokkopi-black"}`}
                >
                  <span className="text-4xl">{t.icon}</span>
                  <span className="font-black">{t.label}</span>
                  <span className="text-xs text-gray-500 font-bold">{t.desc}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-6 pt-4 border-t-4 border-kokkopi-black">
            <label className="block text-xl font-black uppercase tracking-widest">Connect your business</label>
            <div>
              <label className="block font-bold text-gray-600 mb-2 text-sm uppercase tracking-wider">Website URL *</label>
              <input
                id="agent_website_url"
                type="url"
                required
                value={websiteUrl}
                onChange={e => setWebsiteUrl(e.target.value)}
                className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold text-lg focus:outline-none focus:border-kokkopi-blue"
                placeholder="https://example.com"
              />
            </div>
            <div>
              <label className="block font-bold text-gray-600 mb-2 text-sm uppercase tracking-wider">Sitemap URL (optional — speeds up crawl)</label>
              <input
                id="agent_sitemap_url"
                type="url"
                value={sitemapUrl}
                onChange={e => setSitemapUrl(e.target.value)}
                className="w-full border-2 border-kokkopi-black/30 px-4 py-3 font-bold text-lg focus:outline-none focus:border-kokkopi-blue"
                placeholder="https://example.com/sitemap.xml"
              />
            </div>
          </div>

          <div className="flex items-start gap-4 p-5 bg-gray-50 border-2 border-kokkopi-black">
            <input
              type="checkbox"
              id="consent_new"
              checked={consent}
              onChange={e => setConsent(e.target.checked)}
              className="mt-1 w-6 h-6 accent-kokkopi-red"
            />
            <label htmlFor="consent_new" className="font-bold text-lg cursor-pointer leading-snug">
              I authorize Kokkopi to crawl and process this website to train my AI agent.
            </label>
          </div>

          {error && (
            <div className="bg-kokkopi-red/10 border-2 border-kokkopi-red p-4 font-bold text-kokkopi-red">{error}</div>
          )}

          <button
            id="create_agent_submit"
            type="submit"
            disabled={loading}
            className="w-full bg-kokkopi-red text-kokkopi-white font-black py-5 text-2xl uppercase tracking-widest hover:bg-kokkopi-black transition-colors disabled:opacity-50"
          >
            {loading ? "Creating agent..." : "Learn my business →"}
          </button>
        </form>
      </main>
    </div>
  )
}
