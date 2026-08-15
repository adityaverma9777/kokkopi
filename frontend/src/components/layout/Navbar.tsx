"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { logout, getToken } from "@/lib/api"
import { useEffect, useState } from "react"

export function Navbar() {
  const pathname = usePathname()
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    setIsLoggedIn(!!getToken())
  }, [])

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/")

  return (
    <header className="border-b-2 border-kokkopi-black bg-kokkopi-white h-20 flex items-center px-8 justify-between sticky top-0 z-50">
      <div className="flex items-center gap-10">
        <Link href={isLoggedIn ? "/dashboard" : "/"} className="text-3xl font-black tracking-tighter hover:text-kokkopi-red transition-colors">
          kokkopi<span className="text-kokkopi-red">.</span>
        </Link>
        {isLoggedIn && (
          <nav className="hidden md:flex items-center gap-2 font-bold text-lg">
            <Link
              href="/dashboard"
              className={`px-4 py-2 border-2 transition-all ${isActive("/dashboard") ? "bg-kokkopi-yellow border-kokkopi-black" : "border-transparent hover:bg-kokkopi-yellow hover:border-kokkopi-black"}`}
            >
              Agents
            </Link>
            <Link
              href="/settings"
              className={`px-4 py-2 border-2 transition-all ${isActive("/settings") ? "bg-kokkopi-blue text-kokkopi-white border-kokkopi-black" : "border-transparent hover:bg-kokkopi-blue hover:text-kokkopi-white hover:border-kokkopi-black"}`}
            >
              Settings
            </Link>
          </nav>
        )}
      </div>
      <div className="flex items-center gap-4">
        {isLoggedIn ? (
          <button
            onClick={logout}
            className="font-black text-sm border-2 border-kokkopi-black px-4 py-2 hover:bg-kokkopi-red hover:text-kokkopi-white hover:border-kokkopi-red transition-all"
          >
            Sign out
          </button>
        ) : (
          <div className="flex gap-3">
            <Link href="/login" className="font-black text-sm border-2 border-kokkopi-black px-4 py-2 hover:bg-kokkopi-yellow transition-all">Sign in</Link>
            <Link href="/signup" className="font-black text-sm border-2 border-kokkopi-black px-4 py-2 bg-kokkopi-red text-kokkopi-white hover:bg-kokkopi-black transition-all">Sign up</Link>
          </div>
        )}
      </div>
    </header>
  )
}
