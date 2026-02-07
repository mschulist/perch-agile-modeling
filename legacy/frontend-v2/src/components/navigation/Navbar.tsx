'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '../auth/Auth'
import { NavPages } from './NavPages'
import { ProjectSelector } from './ProjectSelector'
import { UserIcon } from './UserIcon'
import Image from 'next/image'

export function Navbar() {
  const user = useAuth()

  const router = useRouter()
  return (
    <div>
      {user ? (
        <div className='navbar px-8 flex items-center justify-between'>
          <div className='flex'>
            <Image
              src='/logo.png'
              alt='logo'
              width={75}
              height={75}
              className='rounded-lg my-2 cursor-pointer transition-opacity duration-200 hover:opacity-80 hover:shadow-lg'
              onClick={() => router.push('/')}
            />
          </div>

          <div className=' flex justify-center'>
            <NavPages />
          </div>

          <div className=' flex justify-end items-center gap-4'>
            <ProjectSelector />
            <UserIcon />
          </div>
        </div>
      ) : (
        <></>
      )}
    </div>
  )
}
