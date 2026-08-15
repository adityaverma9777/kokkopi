import { Navbar } from "@/components/layout/Navbar"
import Link from "next/link"
import { Badge } from "@/components/ui/Badge"

export default function AgentLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { id: string }
}) {
  const agentId = params.id
  
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      
      <div className="border-b-2 border-kokkopi-black bg-kokkopi-white sticky top-20 z-40">
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-black">Smart Buddy</h1>
            <Badge variant="success">Active</Badge>
          </div>
          <nav className="flex items-center gap-2 font-bold">
            <Link href={`/agents/${agentId}/knowledge`} className="px-4 py-2 hover:bg-kokkopi-yellow border-2 border-transparent hover:border-kokkopi-black transition-all">Knowledge</Link>
            <Link href={`/agents/${agentId}/test`} className="px-4 py-2 hover:bg-kokkopi-yellow border-2 border-transparent hover:border-kokkopi-black transition-all">Test</Link>
            <Link href={`/agents/${agentId}/voice`} className="px-4 py-2 hover:bg-kokkopi-yellow border-2 border-transparent hover:border-kokkopi-black transition-all">Voice</Link>
            <Link href={`/agents/${agentId}/customize`} className="px-4 py-2 hover:bg-kokkopi-yellow border-2 border-transparent hover:border-kokkopi-black transition-all">Customize</Link>
            <Link href={`/agents/${agentId}/deploy`} className="px-4 py-2 bg-kokkopi-black text-kokkopi-white border-2 border-kokkopi-black hover:bg-kokkopi-red hover:border-kokkopi-black transition-all">Deploy</Link>
          </nav>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-8">
        {children}
      </main>
    </div>
  )
}
