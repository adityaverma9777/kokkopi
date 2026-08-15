"use client"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Input } from "@/components/ui/Input"
import { useEffect, useState, useRef } from "react"

interface Voice {
  id: string
  name: string
  description: string
  gender: string
  accent: string
  preview_text: string
}

interface DspPreset {
  id: string
  label: string
  icon: string
  description: string
}

export default function VoicePage({ params }: { params: { id: string } }) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [presets, setPresets] = useState<DspPreset[]>([])
  const [selectedVoice, setSelectedVoice] = useState<string>("")
  const [selectedPreset, setSelectedPreset] = useState<string>("broadcast")
  const [previewing, setPreviewing] = useState<string | null>(null)
  const [consent, setConsent] = useState(false)
  const [cloneFile, setCloneFile] = useState<File | null>(null)
  const [cloning, setCloning] = useState(false)
  const [cloneResult, setCloneResult] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    fetch("/api/voice/gallery", { credentials: "include" })
      .then(r => r.json())
      .then(d => { setVoices(d.voices || []); setSelectedVoice(d.voices?.[0]?.id || "") })
      .catch(() => {})

    fetch("/api/voice/effects", { credentials: "include" })
      .then(r => r.json())
      .then(d => setPresets(d.presets || []))
      .catch(() => {})
  }, [])

  const handlePreview = async (voice: Voice) => {
    setPreviewing(voice.id)
    try {
      const res = await fetch(`/api/voice/gallery/${voice.id}/preview?text=${encodeURIComponent(voice.preview_text)}`, { credentials: "include" })
      if (!res.ok) throw new Error("Preview failed")
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      if (audioRef.current) {
        audioRef.current.src = url
        audioRef.current.play()
      }
    } catch {
      alert("Preview unavailable — is the backend TTS running?")
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
      if (res.ok) {
        setCloneResult(`✓ Voice created! Duration: ${data.duration_s?.toFixed(1)}s`)
      } else {
        setCloneResult(`Error: ${data.detail?.message || data.detail}`)
      }
    } catch {
      setCloneResult("Failed to connect to backend.")
    } finally {
      setCloning(false)
    }
  }

  return (
    <div className="space-y-12">
      <audio ref={audioRef} hidden />
      <div>
        <h2 className="text-4xl font-black mb-2">Voice</h2>
        <p className="text-xl font-medium text-gray-600">Give your agent a voice your customers will remember.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">

        <div className="md:col-span-1 space-y-6">
          <Card className="flex flex-col gap-4 border-kokkopi-blue">
            <h3 className="text-xl font-black">Selected Voice</h3>
            {selectedVoice ? (
              <div className="bg-gray-50 p-4 border-2 border-kokkopi-black/10 flex items-center justify-between">
                <span className="font-bold text-lg">{voices.find(v => v.id === selectedVoice)?.name ?? "Loading..."}</span>
                <Badge variant="info">Active</Badge>
              </div>
            ) : (
              <div className="text-gray-500 font-bold">Loading voices...</div>
            )}
          </Card>

          <Card className="flex flex-col gap-4">
            <h3 className="text-xl font-black">Audio Style</h3>
            <p className="text-sm font-medium text-gray-600">DSP processing applied to all voice output.</p>
            {presets.map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedPreset(p.id)}
                className={`w-full text-left p-3 border-2 transition-all font-bold text-sm flex gap-2 items-center ${selectedPreset === p.id ? "border-kokkopi-black bg-kokkopi-yellow" : "border-kokkopi-black/10 hover:border-kokkopi-black"}`}
              >
                <span>{p.icon}</span>
                <span>{p.label}</span>
              </button>
            ))}
          </Card>
        </div>

        <div className="md:col-span-2 space-y-6">
          <Card className="flex flex-col gap-6">
            <h3 className="text-2xl font-black">Choose a voice</h3>
            <div className="grid sm:grid-cols-2 gap-4">
              {voices.map(v => (
                <div
                  key={v.id}
                  onClick={() => setSelectedVoice(v.id)}
                  className={`flex items-center justify-between p-4 border-2 transition-all cursor-pointer group ${selectedVoice === v.id ? "border-kokkopi-black bg-kokkopi-yellow" : "border-kokkopi-black/10 hover:border-kokkopi-black"}`}
                >
                  <div>
                    <p className="font-bold">{v.name}</p>
                    <p className="text-xs text-gray-500">{v.accent} · {v.gender}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handlePreview(v) }}
                    disabled={previewing === v.id}
                    className="w-8 h-8 rounded-full border-2 border-kokkopi-black bg-kokkopi-white flex items-center justify-center font-black group-hover:bg-kokkopi-yellow transition-colors disabled:opacity-50"
                  >
                    {previewing === v.id ? "…" : "▶"}
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card className="flex flex-col gap-4">
            <h3 className="text-xl font-black">Clone a voice</h3>
            <p className="text-sm font-medium text-gray-600">Upload a clean 5–30 second audio sample to create a custom voice for this agent.</p>

            <div
              className="border-2 border-dashed border-kokkopi-black/20 p-6 flex flex-col items-center justify-center text-center hover:border-kokkopi-black transition-colors bg-gray-50 cursor-pointer h-32 mt-2"
              onClick={() => document.getElementById("clone_audio_input")?.click()}
            >
              <input
                id="clone_audio_input"
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={e => setCloneFile(e.target.files?.[0] || null)}
              />
              {cloneFile ? (
                <span className="font-bold text-kokkopi-teal">✓ {cloneFile.name}</span>
              ) : (
                <span className="font-bold text-gray-500">Click to upload audio (WAV, MP3, WebM)</span>
              )}
            </div>

            <div className="flex items-start gap-3 mt-2">
              <input
                type="checkbox"
                id="consent_voice"
                checked={consent}
                onChange={e => setConsent(e.target.checked)}
                className="mt-1 w-5 h-5 accent-kokkopi-red border-2 border-kokkopi-black"
              />
              <label htmlFor="consent_voice" className="font-bold text-sm cursor-pointer leading-snug">
                I own this voice or have explicit authorization to use it for AI synthesis.
                I understand this creates a synthetic voice model stored by Kokkopi.
              </label>
            </div>

            {cloneResult && (
              <div className={`p-3 border-2 font-bold text-sm ${cloneResult.startsWith("✓") ? "border-kokkopi-teal bg-kokkopi-teal/10 text-kokkopi-teal" : "border-kokkopi-red bg-kokkopi-red/10 text-kokkopi-red"}`}>
                {cloneResult}
              </div>
            )}

            <Button
              onClick={handleClone}
              disabled={!cloneFile || !consent || cloning}
              className="mt-auto bg-kokkopi-red disabled:opacity-50"
            >
              {cloning ? "Creating voice..." : "Create voice"}
            </Button>
          </Card>
        </div>

      </div>
    </div>
  )
}
