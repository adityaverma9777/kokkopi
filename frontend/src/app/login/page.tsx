"use client"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { login } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await login(email, password)
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-kokkopi-black flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="text-4xl font-black text-kokkopi-white tracking-tight">
            KOK<span className="text-kokkopi-red">KOPI</span>
          </Link>
          <p className="text-gray-400 font-bold mt-2">Sign in to your dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-kokkopi-white p-8 border-2 border-kokkopi-white space-y-6">
          <div>
            <label className="block font-black text-sm mb-2 uppercase tracking-widest">Email</label>
            <input
              id="login_email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold focus:outline-none focus:border-kokkopi-red bg-gray-50"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block font-black text-sm mb-2 uppercase tracking-widest">Password</label>
            <input
              id="login_password"
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border-2 border-kokkopi-black px-4 py-3 font-bold focus:outline-none focus:border-kokkopi-red bg-gray-50"
              placeholder="••••••••"
            />
          </div>
          {error && (
            <div className="bg-kokkopi-red/10 border-2 border-kokkopi-red p-3 font-bold text-kokkopi-red text-sm">{error}</div>
          )}
          <button
            id="login_submit"
            type="submit"
            disabled={loading}
            className="w-full bg-kokkopi-red text-kokkopi-white font-black py-4 text-lg uppercase tracking-widest hover:bg-kokkopi-black transition-colors disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-center text-gray-400 font-bold mt-6">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-kokkopi-yellow hover:text-kokkopi-white transition-colors">
            Sign up free
          </Link>
        </p>
      </div>
    </div>
  )
}
