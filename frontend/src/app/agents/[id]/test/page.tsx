"use client"
import { useState, useRef, useEffect } from "react"
import { chatWithAgent } from "@/lib/api"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function TestPage({ params }: { params: { id: string } }) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I'm your AI agent. Ask me anything about your business.", timestamp: new Date() }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => `test_${Date.now()}`)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput("")

    const userMsg: Message = { role: "user", content: text, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    const assistantMsg: Message = { role: "assistant", content: "", timestamp: new Date() }
    setMessages(prev => [...prev, assistantMsg])

    try {
      const res = await chatWithAgent(params.id, text, sessionId)
      if (!res.ok) throw new Error("Chat failed")

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value)
          const lines = chunk.split("\n")
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6)
              if (data === "[DONE]") break
              try {
                const parsed = JSON.parse(data)
                const token = parsed.content || parsed.token || parsed.text || ""
                if (token) {
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: updated[updated.length - 1].content + token,
                    }
                    return updated
                  })
                }
              } catch {
                if (data) {
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: updated[updated.length - 1].content + data,
                    }
                    return updated
                  })
                }
              }
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: "⚠ Could not connect to the agent backend. Make sure the backend is running and your Groq API key is set.",
        }
        return updated
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-4xl font-black mb-2">Test</h2>
        <p className="text-xl font-medium text-gray-600">Chat with your agent as a customer would.</p>
      </div>

      <div className="bg-kokkopi-white border-4 border-kokkopi-black flex flex-col" style={{ height: "65vh" }}>
        <div className="bg-kokkopi-black text-kokkopi-white px-6 py-4 flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-kokkopi-red" />
          <div className="w-3 h-3 rounded-full bg-kokkopi-yellow" />
          <div className="w-3 h-3 rounded-full bg-kokkopi-teal" />
          <span className="font-black ml-2">Agent Chat Preview</span>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] px-5 py-4 font-bold leading-relaxed ${
                msg.role === "user"
                  ? "bg-kokkopi-black text-kokkopi-white"
                  : "bg-gray-100 border-2 border-kokkopi-black/10 text-kokkopi-black"
              }`}>
                {msg.content || (loading && i === messages.length - 1 ? (
                  <span className="flex gap-1">
                    <span className="animate-bounce" style={{ animationDelay: "0ms" }}>●</span>
                    <span className="animate-bounce" style={{ animationDelay: "150ms" }}>●</span>
                    <span className="animate-bounce" style={{ animationDelay: "300ms" }}>●</span>
                  </span>
                ) : "")}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="border-t-4 border-kokkopi-black p-4 flex gap-3">
          <input
            ref={inputRef}
            id="test_chat_input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage()}
            disabled={loading}
            placeholder="Type a message..."
            className="flex-1 border-2 border-kokkopi-black px-4 py-3 font-bold focus:outline-none focus:border-kokkopi-blue disabled:opacity-50"
          />
          <button
            id="test_chat_send"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-kokkopi-red text-kokkopi-white font-black px-6 py-3 uppercase tracking-widest hover:bg-kokkopi-black transition-colors disabled:opacity-30"
          >
            Send
          </button>
        </div>
      </div>

      <div className="bg-gray-50 border-2 border-gray-200 p-4">
        <p className="font-bold text-sm text-gray-500">
          💡 Session ID: <span className="font-mono">{sessionId}</span> — each new session starts fresh.
          Customers on your website get their own persistent session.
        </p>
      </div>
    </div>
  )
}
