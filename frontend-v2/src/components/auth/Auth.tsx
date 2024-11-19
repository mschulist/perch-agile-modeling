'use client'

import { User } from '@/models/auth'
import { createContext, useContext, useEffect, useState } from 'react'
import { getCurrentUser } from '@/networking/server_requests'
import { useRouter } from 'next/navigation'

const AuthContext = createContext<User | null>(null)

export const TOKEN_NAME = 'token'

export function Auth(props: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  const router = useRouter()

  useEffect(() => {
    async function fetchData() {
      const userToken = localStorage.getItem(TOKEN_NAME)
      if (!userToken) {
        router.push('/login')
        return
      }
      const response = await getCurrentUser()
      if (response.status === 401) {
        router.push('/login')
        return
      }
      const user = await response.json()
      setUser(user)
      router.push('/')
    }
    fetchData()
  }, [])

  return (
    <AuthContext.Provider value={user}>{props.children}</AuthContext.Provider>
  )
}

export const useAuth = (): User | null => {
  return useContext(AuthContext)
}
