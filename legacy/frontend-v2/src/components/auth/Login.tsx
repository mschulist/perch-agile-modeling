'use client'

import { loginRequest } from '@/networking/server_requests'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const router = useRouter()

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const urlEncodedData = new URLSearchParams()
      urlEncodedData.append('username', email)
      urlEncodedData.append('password', password)

      const res = await loginRequest(urlEncodedData)
      const data = await res.json()

      if (res.ok) {
        localStorage.setItem('token', data.access_token)
        router.push('/')
        window.location.reload()
      } else {
        setError(data.detail || 'Invalid credentials')
      }
    } catch (err) {
      setError('An error occurred during login')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className='flex flex-col items-center justify-center align-middle h-full gap-3'
    >
      <input
        type='email'
        name='username'
        value={email}
        placeholder='Email'
        className='input input-bordered w-full max-w-xs text-white'
        onChange={(e) => setEmail(e.target.value)}
        disabled={isLoading}
        required
      />
      <input
        type='password'
        name='password'
        value={password}
        placeholder='Password'
        className='input input-bordered w-full max-w-xs text-white'
        onChange={(e) => setPassword(e.target.value)}
        disabled={isLoading}
        required
      />
      <button type='submit' className='btn btn-primary' disabled={isLoading}>
        {isLoading ? (
          <span className='loading loading-dots loading-lg'></span>
        ) : (
          'Login'
        )}
      </button>
      {error && <p className='text-red-500'>{error}</p>}
    </form>
  )
}
