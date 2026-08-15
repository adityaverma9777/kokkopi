"use client"
import { useEffect, useState } from "react"
import { getPronunciation, updatePronunciation } from "@/lib/api"

interface PronunciationEntry {
  term: string
  replacement: string
}

export default function CustomizePage({ params }: { params: { id: string } }) {
  const [entries, setEntries] = useState<PronunciationEntry[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [newTerm, setNewTerm] = useState("")
  const [newReplacement, setNewReplacement] = useState("")
  const [agentName, setAgentName] = useState("My Agent")
  const [greeting, setGreeting] = useState("Hi! I'm your AI assistant. How can I help you today?")
  const [accentColor, setAccentColor] = useState("#FE194E")

  useEffect(() => {
    getPronunciation(params.id).then(data => setEntries(data.entries || []))
  }, [params.id])

  const addEntry = () => {
    if (!newTerm.trim()) return
    setEntries(prev => [...prev, { term: newTerm.trim(), replacement: newReplacement.trim() }])
    setNewTerm("")
    setNewReplacement("")
  }

  const removeEntry = (i: number) => {
    setEntries(prev => prev.filter((_, idx) => idx !== i))
  }

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await updatePronunciation(params.id, entries)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
    } finally {
      setSaving(false)
    }
  }

  const colors = ["#FE194E", "#198EF8", "#FFBC03", "#01695B", "#000407"]

  return (
    <div className="space-y-12">
      <div>
        <h2 className="text-4xl font-black mb-2">Customize</h2>
        <p className="text-xl font-medium text-gray-600">Brand your agent&apos;s personality, style, and speech.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-10">
        <div className="space-y-8">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-6">
            <h3 className="text-xl font-black">Widget Identity</h3>
            <div>
              <label className="block font-black text-sm mb-2 uppercase tracking-widest">Agent display name</label>
              <input
                id="customize_agent_name"
                type="text"
                value={agentName}
                onChange={e => setAgentName(e.target.value)}
                className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold focus:outline-none focus:border-kokkopi-blue"
              />
            </div>
            <div>
              <label className="block font-black text-sm mb-2 uppercase tracking-widest">Opening greeting</label>
              <textarea
                id="customize_greeting"
                value={greeting}
                onChange={e => setGreeting(e.target.value)}
                rows={3}
                className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold focus:outline-none focus:border-kokkopi-blue resize-none"
              />
            </div>
            <div>
              <label className="block font-black text-sm mb-2 uppercase tracking-widest">Accent color</label>
              <div className="flex gap-3">
                {colors.map(c => (
                  <button
                    key={c}
                    onClick={() => setAccentColor(c)}
                    style={{ backgroundColor: c }}
                    className={`w-10 h-10 border-4 transition-all ${accentColor === c ? "border-kokkopi-black scale-110" : "border-transparent"}`}
                  />
                ))}
                <input type="color" value={accentColor} onChange={e => setAccentColor(e.target.value)} className="w-10 h-10 border-2 border-kokkopi-black cursor-pointer" />
              </div>
            </div>
          </div>

          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-6">
            <h3 className="text-xl font-black">Pronunciation Dictionary</h3>
            <p className="text-sm font-bold text-gray-500">Teach your agent how to say your brand names, products, and local terms correctly.</p>

            <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
              <div>
                <label className="block font-black text-xs mb-1 uppercase tracking-widest">Word/phrase</label>
                <input
                  id="pronun_term"
                  type="text"
                  value={newTerm}
                  onChange={e => setNewTerm(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addEntry()}
                  className="w-full border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue"
                  placeholder="Kokkopi"
                />
              </div>
              <div>
                <label className="block font-black text-xs mb-1 uppercase tracking-widest">Sounds like</label>
                <input
                  id="pronun_replacement"
                  type="text"
                  value={newReplacement}
                  onChange={e => setNewReplacement(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addEntry()}
                  className="w-full border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue"
                  placeholder="Koh-koh-pee"
                />
              </div>
              <button onClick={addEntry} className="bg-kokkopi-black text-kokkopi-white font-black px-4 py-2 hover:bg-kokkopi-blue transition-colors text-sm h-[42px]">
                + Add
              </button>
            </div>

            {entries.length > 0 ? (
              <div className="space-y-2">
                {entries.map((e, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 border-2 border-kokkopi-black/10">
                    <span className="font-bold text-sm flex-1">{e.term}</span>
                    <span className="text-gray-400 font-bold text-sm">→</span>
                    <span className="font-bold text-sm flex-1">{e.replacement}</span>
                    <button onClick={() => removeEntry(i)} className="text-kokkopi-red font-black hover:opacity-70 text-sm">✕</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 font-bold text-sm text-center py-4 border-2 border-dashed border-gray-200">
                No pronunciation rules yet. Add one above.
              </div>
            )}

            <button
              id="pronun_save"
              onClick={handleSave}
              disabled={saving}
              className={`w-full font-black py-3 uppercase tracking-widest transition-colors ${saved ? "bg-kokkopi-teal text-kokkopi-white" : "bg-kokkopi-black text-kokkopi-white hover:bg-kokkopi-blue"} disabled:opacity-50`}
            >
              {saved ? "✓ Saved!" : saving ? "Saving..." : "Save pronunciation rules"}
            </button>
          </div>
        </div>

        <div className="md:col-span-1">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-4 sticky top-40">
            <h3 className="text-xl font-black">Widget Preview</h3>
            <div className="border-4 border-kokkopi-black bg-gray-50 p-4" style={{ height: "420px" }}>
              <div className="bg-kokkopi-black rounded-t-none rounded-b-none h-full flex flex-col overflow-hidden">
                <div className="px-5 py-4 text-kokkopi-white font-black" style={{ backgroundColor: accentColor }}>
                  {agentName}
                </div>
                <div className="flex-1 p-4 bg-white overflow-hidden">
                  <div className="bg-gray-100 px-4 py-3 text-sm font-bold inline-block max-w-[85%] border border-gray-200">
                    {greeting}
                  </div>
                </div>
                <div className="border-t-2 border-gray-200 p-3 flex gap-2 bg-white">
                  <div className="flex-1 border border-gray-300 px-3 py-2 text-xs text-gray-400 font-bold">Type a message...</div>
                  <div className="px-3 py-2 text-xs font-black text-white" style={{ backgroundColor: accentColor }}>→</div>
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-500 font-bold text-center">Live preview of your widget appearance</p>
          </div>
        </div>
      </div>
    </div>
  )
}
