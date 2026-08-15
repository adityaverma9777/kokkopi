"use client"
import { useEffect, useState } from "react"
import { getProviderCredential, saveProviderCredential, getSystemStatus } from "@/lib/api"
import { logout, getToken } from "@/lib/api"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Navbar } from "@/components/layout/Navbar"

interface SystemStatus {
  asr: { available: boolean; message: string }
  models: { name: string; vram_mb: number }[]
  vram_used_mb: number
}

export default function SettingsPage() {
  const router = useRouter()
  const [apiKey, setApiKey] = useState("")
  const [showKey, setShowKey] = useState(false)
  const [hasKey, setHasKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState("")
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return }
    getProviderCredential().then(cred => {
      if (cred?.has_key) setHasKey(true)
    })
    getSystemStatus().then(setSystemStatus)
  }, [router])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) return
    setError("")
    setSaving(true)
    try {
      await saveProviderCredential(apiKey.trim())
      setHasKey(true)
      setSaved(true)
      setApiKey("")
      setTimeout(() => setSaved(false), 3000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save API key")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-kokkopi-white">
      <Navbar />
      <main className="flex-1 max-w-3xl w-full mx-auto p-8 pt-16 space-y-10">
        <div>
          <h1 className="text-5xl font-black mb-2">Settings</h1>
          <p className="text-xl font-medium text-gray-600">Configure your Kokkopi workspace.</p>
        </div>

        <div className="bg-kokkopi-white border-4 border-kokkopi-black p-8 space-y-6">
          <h2 className="text-2xl font-black">Groq API Key</h2>
          <p className="font-bold text-gray-600">Kokkopi uses your own Groq key. Your key is encrypted at rest and never logged.</p>

          {hasKey && !saved && (
            <div className="flex items-center gap-3 p-4 bg-kokkopi-teal/10 border-2 border-kokkopi-teal">
              <span className="text-kokkopi-teal font-black text-xl">✓</span>
              <span className="font-bold text-kokkopi-teal">Groq API key is configured</span>
            </div>
          )}
          {saved && (
            <div className="flex items-center gap-3 p-4 bg-kokkopi-teal/10 border-2 border-kokkopi-teal">
              <span className="text-kokkopi-teal font-black text-xl">✓</span>
              <span className="font-bold text-kokkopi-teal">API key saved successfully!</span>
            </div>
          )}

          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block font-black text-sm mb-2 uppercase tracking-widest">
                {hasKey ? "Replace API key" : "Groq API key"}
              </label>
              <div className="relative">
                <input
                  id="settings_api_key"
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold font-mono focus:outline-none focus:border-kokkopi-blue pr-24"
                  placeholder="gsk_••••••••••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 font-bold text-sm text-gray-500 hover:text-kokkopi-black"
                >
                  {showKey ? "Hide" : "Show"}
                </button>
              </div>
              <p className="text-xs text-gray-500 font-bold mt-2">
                Get a free key at{" "}
                <a href="https://console.groq.com" target="_blank" rel="noreferrer" className="text-kokkopi-blue hover:underline">
                  console.groq.com
                </a>
              </p>
            </div>
            {error && <div className="p-3 bg-kokkopi-red/10 border-2 border-kokkopi-red font-bold text-kokkopi-red text-sm">{error}</div>}
            <button
              id="settings_save_key"
              type="submit"
              disabled={saving || !apiKey.trim()}
              className="w-full bg-kokkopi-black text-kokkopi-white font-black py-4 uppercase tracking-widest hover:bg-kokkopi-red transition-colors disabled:opacity-40"
            >
              {saving ? "Saving..." : "Save API key"}
            </button>
          </form>
        </div>

        {systemStatus && (
          <div className="bg-kokkopi-white border-4 border-kokkopi-black p-8 space-y-6">
            <h2 className="text-2xl font-black">System Status</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 border-2 border-kokkopi-black/10">
                <span className="font-bold">ASR (Voice transcription)</span>
                <span className={`font-black text-sm ${systemStatus.asr.available ? "text-kokkopi-teal" : "text-kokkopi-red"}`}>
                  {systemStatus.asr.available ? "● Available" : "● Unavailable"}
                </span>
              </div>
              <div className="flex items-center justify-between p-4 border-2 border-kokkopi-black/10">
                <span className="font-bold">VRAM used</span>
                <span className="font-black">{systemStatus.vram_used_mb?.toFixed(0)} MB</span>
              </div>
              {systemStatus.models.map(m => (
                <div key={m.name} className="flex items-center justify-between p-4 bg-gray-50 border-2 border-kokkopi-black/10">
                  <span className="font-bold font-mono text-sm">{m.name}</span>
                  <span className="font-bold text-sm text-gray-500">{m.vram_mb} MB</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-kokkopi-white border-4 border-kokkopi-black p-8 space-y-4">
          <h2 className="text-2xl font-black">Account</h2>
          <button
            id="settings_logout"
            onClick={logout}
            className="w-full border-4 border-kokkopi-black font-black py-4 uppercase tracking-widest hover:bg-kokkopi-red hover:text-kokkopi-white hover:border-kokkopi-red transition-colors"
          >
            Sign out
          </button>
        </div>
      </main>
    </div>
  )
}
