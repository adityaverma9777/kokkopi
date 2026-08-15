"use client"
import { useEffect, useState, useRef } from "react"
import { getPronunciation, updatePronunciation } from "@/lib/api"

interface Voice {
  id: string
  name: string
  description: string
  gender: string
  lang_code: string
  language: string
  language_flag: string
  tags: string[]
  preview_text?: string
}

interface DspPreset {
  id: string
  label: string
  icon: string
  description: string
}

interface Language {
  code: string
  name: string
  flag: string
}

export default function VoicePage({ params }: { params: { id: string } }) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [presets, setPresets] = useState<DspPreset[]>([])
  const [selectedVoice, setSelectedVoice] = useState<string>("")
  const [selectedPreset, setSelectedPreset] = useState<string>("broadcast")
  const [filterLang, setFilterLang] = useState<string>("all")
  const [filterGender, setFilterGender] = useState<string>("all")
  const [previewing, setPreviewing] = useState<string | null>(null)
  const [languages, setLanguages] = useState<Language[]>([])
  const [consent, setConsent] = useState(false)
  const [cloneFile, setCloneFile] = useState<File | null>(null)
  const [cloning, setCloning] = useState(false)
  const [cloneResult, setCloneResult] = useState<string | null>(null)
  const [pronunEntries, setPronunEntries] = useState<{ term: string; replacement: string }[]>([])
  const [newTerm, setNewTerm] = useState("")
  const [newReplacement, setNewReplacement] = useState("")
  const [pronunSaved, setPronunSaved] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    fetch("/api/voice/gallery", { credentials: "include" })
      .then(r => r.json())
      .then(d => {
        const v: Voice[] = d.voices || []
        setVoices(v)
        setSelectedVoice(v[0]?.id || "")
        const langCodes: string[] = d.languages || []
        const langMap: Record<string, string> = {
          "en-us": "English (US)", "en-gb": "English (UK)", "es-es": "Español",
          "fr-fr": "Français", "ja": "日本語", "zh-cn": "中文", "ko": "한국어",
          "pt-br": "Português", "hi": "हिंदी",
        }
        const flagMap: Record<string, string> = {
          "en-us": "🇺🇸", "en-gb": "🇬🇧", "es-es": "🇪🇸", "fr-fr": "🇫🇷",
          "ja": "🇯🇵", "zh-cn": "🇨🇳", "ko": "🇰🇷", "pt-br": "🇧🇷", "hi": "🇮🇳",
        }
        setLanguages(langCodes.map(code => ({
          code,
          name: langMap[code] || code,
          flag: flagMap[code] || "🌐",
        })))
      }).catch(() => {})

    fetch("/api/voice/effects", { credentials: "include" })
      .then(r => r.json())
      .then(d => setPresets(d.presets || []))
      .catch(() => {})

    getPronunciation(params.id).then(d => setPronunEntries(d.entries || []))
  }, [params.id])

  const filteredVoices = voices.filter(v => {
    const langOk = filterLang === "all" || v.lang_code === filterLang
    const genderOk = filterGender === "all" || v.gender === filterGender
    return langOk && genderOk
  })

  const handlePreview = async (voice: Voice) => {
    setPreviewing(voice.id)
    try {
      const res = await fetch(`/api/voice/gallery/${voice.id}/preview`, { credentials: "include" })
      if (!res.ok) throw new Error()
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      if (audioRef.current) {
        audioRef.current.src = url
        audioRef.current.play()
      }
    } catch {
      alert("Preview unavailable — make sure Kokoro TTS is running on the backend.")
    } finally {
      setPreviewing(null)
    }
  }

  const handleClone = async () => {
    if (!cloneFile || !consent) return
    setCloning(true)
    setCloneResult(null)
    try {
      const form = new FormData()
      form.append("agent_id", params.id)
      form.append("profile_name", "Custom Voice")
      form.append("consent_confirmed", "true")
      form.append("audio", cloneFile)
      const res = await fetch("/api/voice/clone", { method: "POST", credentials: "include", body: form })
      const data = await res.json()
      if (res.ok) setCloneResult(`✓ Voice profile created (${data.duration_s?.toFixed(1)}s)`)
      else setCloneResult(`Error: ${data.detail?.message || data.detail}`)
    } catch {
      setCloneResult("Failed to connect to backend.")
    } finally {
      setCloning(false)
    }
  }

  const addPronun = () => {
    if (!newTerm.trim()) return
    setPronunEntries(p => [...p, { term: newTerm.trim(), replacement: newReplacement.trim() }])
    setNewTerm(""); setNewReplacement("")
  }

  const savePronun = async () => {
    await updatePronunciation(params.id, pronunEntries)
    setPronunSaved(true)
    setTimeout(() => setPronunSaved(false), 3000)
  }

  const selectedVoiceMeta = voices.find(v => v.id === selectedVoice)

  return (
    <div className="space-y-12">
      <audio ref={audioRef} hidden />
      <div>
        <h2 className="text-4xl font-black mb-2">Voice</h2>
        <p className="text-xl font-medium text-gray-600">
          Choose a voice in any language. Your agent automatically speaks the visitor&apos;s language.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">

        <div className="md:col-span-1 space-y-4">
          <div className="bg-kokkopi-black text-kokkopi-white p-6 space-y-4 border-4 border-kokkopi-black">
            <h3 className="text-xl font-black">Active Voice</h3>
            {selectedVoiceMeta ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{selectedVoiceMeta.language_flag}</span>
                  <div>
                    <p className="font-black text-lg">{selectedVoiceMeta.name}</p>
                    <p className="text-gray-400 font-bold text-sm">{selectedVoiceMeta.language}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {selectedVoiceMeta.tags?.map(tag => (
                    <span key={tag} className="text-xs font-bold bg-gray-800 text-gray-300 px-2 py-1">{tag}</span>
                  ))}
                </div>
              </div>
            ) : <p className="text-gray-400 font-bold">No voice selected</p>}
          </div>

          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-3">
            <h3 className="text-lg font-black">Multilingual AI</h3>
            <p className="text-sm font-bold text-gray-600 leading-relaxed">
              Your agent automatically detects the visitor&apos;s language and responds in the same language — no setup required.
            </p>
            <div className="grid grid-cols-3 gap-1">
              {["🇺🇸", "🇬🇧", "🇪🇸", "🇫🇷", "🇯🇵", "🇨🇳", "🇰🇷", "🇧🇷", "🇮🇳"].map(flag => (
                <div key={flag} className="text-center py-2 border border-gray-100 text-xl">{flag}</div>
              ))}
            </div>
          </div>

          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-5 space-y-3">
            <h3 className="text-lg font-black">Audio Style</h3>
            {presets.map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedPreset(p.id)}
                className={`w-full text-left p-3 border-2 transition-all font-bold text-sm flex gap-2 items-center ${selectedPreset === p.id ? "border-kokkopi-black bg-kokkopi-yellow" : "border-kokkopi-black/10 hover:border-kokkopi-black"}`}
              >
                <span>{p.icon}</span><span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="md:col-span-2 space-y-6">
          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-5">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <h3 className="text-2xl font-black">Voice gallery</h3>
              <div className="flex gap-2">
                <select
                  value={filterLang}
                  onChange={e => setFilterLang(e.target.value)}
                  className="border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue"
                >
                  <option value="all">All languages</option>
                  {languages.map(l => (
                    <option key={l.code} value={l.code}>{l.flag} {l.name}</option>
                  ))}
                </select>
                <select
                  value={filterGender}
                  onChange={e => setFilterGender(e.target.value)}
                  className="border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue"
                >
                  <option value="all">All genders</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                </select>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 max-h-[440px] overflow-y-auto pr-1">
              {filteredVoices.map(v => (
                <div
                  key={v.id}
                  onClick={() => setSelectedVoice(v.id)}
                  className={`flex items-center justify-between p-4 border-2 cursor-pointer transition-all group ${selectedVoice === v.id ? "border-kokkopi-black bg-kokkopi-yellow" : "border-kokkopi-black/10 hover:border-kokkopi-black"}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{v.language_flag}</span>
                    <div>
                      <p className="font-black">{v.name}</p>
                      <p className="text-xs text-gray-500 font-bold">{v.language} · {v.gender}</p>
                    </div>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); handlePreview(v) }}
                    disabled={previewing === v.id}
                    className="w-8 h-8 border-2 border-kokkopi-black flex items-center justify-center font-black hover:bg-kokkopi-black hover:text-kokkopi-white transition-colors disabled:opacity-40 text-sm flex-shrink-0"
                  >
                    {previewing === v.id ? "…" : "▶"}
                  </button>
                </div>
              ))}
              {filteredVoices.length === 0 && (
                <div className="col-span-2 text-center py-8 text-gray-400 font-bold">No voices match this filter.</div>
              )}
            </div>
          </div>

          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-5">
            <h3 className="text-xl font-black">Clone a voice</h3>
            <p className="text-sm font-bold text-gray-600">Upload 5–30 seconds of clear speech to clone a custom voice for this agent.</p>

            <div
              className="border-2 border-dashed border-kokkopi-black/20 p-6 flex flex-col items-center justify-center text-center hover:border-kokkopi-black transition-colors bg-gray-50 cursor-pointer h-28"
              onClick={() => document.getElementById("clone_audio_input")?.click()}
            >
              <input id="clone_audio_input" type="file" accept="audio/*" className="hidden" onChange={e => setCloneFile(e.target.files?.[0] || null)} />
              {cloneFile ? (
                <span className="font-bold text-kokkopi-teal">✓ {cloneFile.name}</span>
              ) : (
                <span className="font-bold text-gray-500">Click to upload audio (WAV, MP3, WebM, FLAC)</span>
              )}
            </div>

            <div className="flex items-start gap-3">
              <input type="checkbox" id="consent_voice" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1 w-5 h-5 accent-kokkopi-red" />
              <label htmlFor="consent_voice" className="font-bold text-sm cursor-pointer leading-snug">
                I own this voice or have explicit authorization to use it for AI voice synthesis.
              </label>
            </div>

            {cloneResult && (
              <div className={`p-3 border-2 font-bold text-sm ${cloneResult.startsWith("✓") ? "border-kokkopi-teal bg-kokkopi-teal/10 text-kokkopi-teal" : "border-kokkopi-red bg-kokkopi-red/10 text-kokkopi-red"}`}>
                {cloneResult}
              </div>
            )}

            <button
              onClick={handleClone}
              disabled={!cloneFile || !consent || cloning}
              className="w-full bg-kokkopi-red text-kokkopi-white font-black py-4 uppercase tracking-widest hover:bg-kokkopi-black transition-colors disabled:opacity-40"
            >
              {cloning ? "Processing..." : "Create voice"}
            </button>
          </div>

          <div className="bg-kokkopi-white border-2 border-kokkopi-black p-6 space-y-5">
            <h3 className="text-xl font-black">Pronunciation dictionary</h3>
            <p className="text-sm font-bold text-gray-600">Teach your agent how to pronounce brand names and local terms correctly.</p>

            <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
              <div>
                <label className="block font-black text-xs mb-1 uppercase tracking-widest">Word</label>
                <input id="pronun_term" type="text" value={newTerm} onChange={e => setNewTerm(e.target.value)} onKeyDown={e => e.key === "Enter" && addPronun()} className="w-full border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue" placeholder="Kokkopi" />
              </div>
              <div>
                <label className="block font-black text-xs mb-1 uppercase tracking-widest">Sounds like</label>
                <input id="pronun_replacement" type="text" value={newReplacement} onChange={e => setNewReplacement(e.target.value)} onKeyDown={e => e.key === "Enter" && addPronun()} className="w-full border-2 border-kokkopi-black px-3 py-2 font-bold text-sm focus:outline-none focus:border-kokkopi-blue" placeholder="Koh-koh-pee" />
              </div>
              <button onClick={addPronun} className="bg-kokkopi-black text-kokkopi-white font-black px-4 py-2 hover:bg-kokkopi-blue transition-colors text-sm h-[42px]">+ Add</button>
            </div>

            {pronunEntries.length > 0 ? (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {pronunEntries.map((e, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 border-2 border-kokkopi-black/10">
                    <span className="font-bold text-sm flex-1">{e.term}</span>
                    <span className="text-gray-400 font-bold text-sm">→</span>
                    <span className="font-bold text-sm flex-1">{e.replacement}</span>
                    <button onClick={() => setPronunEntries(p => p.filter((_, idx) => idx !== i))} className="text-kokkopi-red font-black text-sm hover:opacity-70">✕</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 font-bold text-sm text-center py-3 border-2 border-dashed border-gray-200">No rules yet.</div>
            )}

            <button
              onClick={savePronun}
              className={`w-full font-black py-3 uppercase tracking-widest transition-colors ${pronunSaved ? "bg-kokkopi-teal text-kokkopi-white" : "bg-kokkopi-black text-kokkopi-white hover:bg-kokkopi-blue"}`}
            >
              {pronunSaved ? "✓ Saved!" : "Save pronunciation rules"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
