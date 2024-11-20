'use client'

import { useAuth } from '../auth/Auth'

export function UserIcon() {
  const user = useAuth()

  function signOut() {
    localStorage.removeItem('token')
    window.location.reload()
  }

  return (
    <div className='group relative cursor-pointer flex items-center justify-center'>
      <span className='text-lg transition-opacity duration-300 group-hover:opacity-0'>
        Welcome, {user?.name}!
      </span>
      <button
        onClick={signOut}
        className='absolute text-lg hover:text-red-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100'
      >
        Sign Out
      </button>
    </div>
  )
}
