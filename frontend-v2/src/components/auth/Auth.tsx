'use client'

import { User } from '@/models/auth'
import { createContext, useEffect, useState } from 'react'
import { getCurrentUser } from '@/networking/server_requests'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'

const authContext = createContext<User | null>(null)

export const TOKEN_NAME = 'access_token'

export function Auth(props: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  const router = useRouter()

  useEffect(() => {
    async function fetchData() {
      const userCookie = Cookies.get(TOKEN_NAME)
      console.log(userCookie)
      if (!userCookie) {
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
    }
    fetchData()
  }, [user, router])

  return (
    <authContext.Provider value={user}>{props.children}</authContext.Provider>
  )
}
