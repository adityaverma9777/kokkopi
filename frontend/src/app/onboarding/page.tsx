import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import Link from "next/link"

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-kokkopi-yellow flex items-center justify-center p-8">
      <div className="max-w-4xl w-full grid md:grid-cols-2 gap-8 items-center">
        
        {/* Left Side: Graphic / Illustration area */}
        <div className="hidden md:flex flex-col justify-center">
          <h1 className="text-6xl font-black mb-6 leading-tight">
            Teach Kokkopi<br/>your business.
          </h1>
          <p className="text-2xl font-bold mb-8">
            Enter your website and we'll do the rest.
          </p>
          {/* Placeholder for Rooster artwork */}
          <div className="w-64 h-64 bg-kokkopi-black rounded-full flex items-center justify-center text-kokkopi-white text-4xl font-black shadow-brand transform -rotate-6">
            🐓
          </div>
        </div>

        {/* Right Side: Form */}
        <Card className="border-4 p-8 flex flex-col gap-6 shadow-[8px_8px_0px_0px_rgba(0,4,7,1)]">
          <div>
            <h2 className="text-3xl font-black mb-2">Step 1: AI Provider</h2>
            <p className="font-medium text-gray-600">Connect your Groq account to power the intelligence.</p>
          </div>
          
          <div className="space-y-4">
            <label className="block font-bold text-lg">Groq API Key</label>
            <Input type="password" placeholder="gsk_..." />
          </div>

          <div className="border-t-2 border-kokkopi-black my-4"></div>

          <div>
            <h2 className="text-3xl font-black mb-2">Step 2: Business Website</h2>
            <p className="font-medium text-gray-600">Where should Kokkopi learn about you?</p>
          </div>

          <div className="space-y-4">
            <label className="block font-bold text-lg">Website URL</label>
            <Input type="url" placeholder="https://example.com" />
          </div>

          <div className="flex items-start gap-3 mt-4">
            <input type="checkbox" id="consent" className="mt-1 w-5 h-5 accent-kokkopi-red border-2 border-kokkopi-black" />
            <label htmlFor="consent" className="font-bold cursor-pointer">
              I authorize Kokkopi to crawl and process this website.
            </label>
          </div>

          <Link href="/dashboard" className="mt-4">
            <Button size="lg" className="w-full text-xl bg-kokkopi-red">Teach my business →</Button>
          </Link>
        </Card>

      </div>
    </div>
  )
}
