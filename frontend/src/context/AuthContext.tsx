"use client"
import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { getToken, logout } from "@/lib/api"

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  token: string | null
  signOut: () => void
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  token: null,
  signOut: logout,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const t = getToken()
    setToken(t)
    setIsLoading(false)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, isLoading, token, signOut: logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
