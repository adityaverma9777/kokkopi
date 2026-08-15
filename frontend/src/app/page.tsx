import { Navbar } from "@/components/layout/Navbar"
import { Button } from "@/components/ui/Button"
import Link from "next/link"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      
      <main className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-kokkopi-white">
        
        <div className="max-w-4xl space-y-8">
          <h1 className="text-7xl md:text-8xl font-black tracking-tighter leading-none">
            Your website.<br/>
            Your knowledge.<br/>
            <span className="text-kokkopi-red">Your AI.</span>
          </h1>
          
          <p className="text-2xl font-bold text-gray-700 max-w-2xl mx-auto">
            Give Kokkopi your website URL and we'll turn it into a fully conversational AI employee with chat and voice.
          </p>
          
          <div className="pt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/onboarding">
              <Button size="lg" className="text-2xl h-16 px-12 shadow-[8px_8px_0px_0px_rgba(0,4,7,1)] hover:shadow-[4px_4px_0px_0px_rgba(0,4,7,1)] hover:translate-y-1 hover:translate-x-1 transition-all bg-kokkopi-red">
                Get Started
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="secondary" size="lg" className="text-xl h-16 px-8">
                Go to Dashboard
              </Button>
            </Link>
          </div>
        </div>

      </main>
    </div>
  );
}
