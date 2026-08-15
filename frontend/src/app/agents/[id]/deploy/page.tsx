"use client"
import { useEffect, useState } from "react"
import { getAgent } from "@/lib/api"

interface Agent {
  id: string
  name: string
  website_url: string
  public_agent_id?: string
  status: string
}

export default function DeployPage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [copied, setCopied] = useState(false)
  const widgetBase = process.env.NEXT_PUBLIC_WIDGET_URL || "https://your-hf-space.hf.space/widget.js"

  useEffect(() => {
    getAgent(params.id).then(setAgent)
  }, [params.id])

  const publicId = agent?.public_agent_id || params.id
  const scriptTag = `<script\n  src="${widgetBase}"\n  data-agent="${publicId}"\n></script>`

  const handleCopy = () => {
    navigator.clipboard.writeText(scriptTag).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  return (
    <div className="space-y-12">
      <div>
        <h2 className="text-4xl font-black mb-2">Deploy</h2>
        <p className="text-xl font-medium text-gray-600">Put your agent on your website in 30 seconds.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-8">

          <div className="bg-kokkopi-black text-kokkopi-white border-4 border-kokkopi-black p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-kokkopi-red text-kokkopi-white font-black flex items-center justify-center text-lg">1</div>
              <h3 className="text-2xl font-black">Copy the script tag</h3>
            </div>
            <div className="bg-gray-900 p-6 font-mono text-sm text-green-400 whitespace-pre leading-relaxed border-2 border-gray-700 overflow-x-auto">
              {scriptTag}
            </div>
            <button
              id="deploy_copy_btn"
              onClick={handleCopy}
              className={`w-full font-black py-4 text-lg uppercase tracking-widest transition-colors ${copied ? "bg-kokkopi-teal text-kokkopi-white" : "bg-kokkopi-red text-kokkopi-white hover:bg-kokkopi-yellow hover:text-kokkopi-black"}`}
            >
              {copied ? "✓ Copied to clipboard!" : "Copy script tag"}
            </button>
          </div>

          <div className="bg-kokkopi-white border-4 border-kokkopi-black p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-kokkopi-black text-kokkopi-white font-black flex items-center justify-center text-lg">2</div>
              <h3 className="text-2xl font-black">Paste it before &lt;/body&gt;</h3>
            </div>
            <div className="bg-gray-50 border-2 border-kokkopi-black/20 p-6 font-mono text-sm leading-relaxed text-gray-700 overflow-x-auto">
              <span className="text-gray-400">{`<!DOCTYPE html>\n<html>\n  <head>...</head>\n  <body>\n    ...\n\n    `}</span>
              <span className="bg-kokkopi-yellow px-1 text-kokkopi-black">{`<script src="${widgetBase}" data-agent="${publicId}"></script>`}</span>
              <span className="text-gray-400">{`\n  </body>\n</html>`}</span>
            </div>
          </div>

          <div className="bg-kokkopi-white border-4 border-kokkopi-black p-8 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-kokkopi-black text-kokkopi-white font-black flex items-center justify-center text-lg">3</div>
              <h3 className="text-2xl font-black">Your agent is live!</h3>
            </div>
            <p className="font-bold text-gray-600">The Kokkopi widget will appear in the bottom-right corner of your website automatically. No other configuration needed.</p>
            <div className="grid grid-cols-3 gap-4 pt-4">
              {[["0", "Setup time"], ["∞", "Conversations"], ["Auto", "Updates"]].map(([val, label]) => (
                <div key={label} className="text-center border-2 border-kokkopi-black p-4">
                  <div className="text-3xl font-black text-kokkopi-red">{val}</div>
                  <div className="text-sm font-bold text-gray-500 mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="md:col-span-1 space-y-6">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-4">
            <h3 className="text-xl font-black">Agent Details</h3>
            <div className="space-y-3 text-sm">
              <div className="flex flex-col gap-1 py-2 border-b border-kokkopi-black/10">
                <span className="font-black uppercase tracking-wider text-gray-500 text-xs">Agent</span>
                <span className="font-bold">{agent?.name || "Loading..."}</span>
              </div>
              <div className="flex flex-col gap-1 py-2 border-b border-kokkopi-black/10">
                <span className="font-black uppercase tracking-wider text-gray-500 text-xs">Agent ID</span>
                <span className="font-mono text-xs break-all">{publicId}</span>
              </div>
              <div className="flex flex-col gap-1 py-2 border-b border-kokkopi-black/10">
                <span className="font-black uppercase tracking-wider text-gray-500 text-xs">Website</span>
                <a href={agent?.website_url} target="_blank" rel="noreferrer" className="text-kokkopi-blue hover:underline font-bold truncate">
                  {agent?.website_url?.replace(/^https?:\/\//, "") || "—"}
                </a>
              </div>
              <div className="flex flex-col gap-1 py-2">
                <span className="font-black uppercase tracking-wider text-gray-500 text-xs">Status</span>
                <span className={`font-black text-sm ${agent?.status === "active" ? "text-kokkopi-teal" : "text-gray-400"}`}>
                  {agent?.status === "active" ? "● Active" : "● Not deployed"}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-kokkopi-yellow border-4 border-kokkopi-black p-6 space-y-3">
            <h3 className="text-lg font-black">Need help?</h3>
            <ul className="space-y-2 text-sm font-bold">
              <li>→ Paste the tag in Webflow, Wix, Framer, Shopify, or any custom site</li>
              <li>→ Works with React, Vue, Svelte — no framework dependency</li>
              <li>→ The widget is &lt;12 KB compressed</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
