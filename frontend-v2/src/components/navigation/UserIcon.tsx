'use client'

import { useAuth } from '../auth/Auth'

export function UserIcon() {
  const user = useAuth()

  return (
    <div className="flex items-center">
      <span className="ml-2 text-lg">Welcome, {user?.name}!</span>
    </div>
  )
}
