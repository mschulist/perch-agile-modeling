'use client'

import { useAuth } from '../auth/Auth'
import { NavPages } from './NavPages'
import { ProjectSelector } from './ProjectSelector'
import { UserIcon } from './UserIcon'

export function Navbar() {
  const user = useAuth()
  return (
    <div>
      {user
        ? (
          <div className='navbar px-8 flex items-center justify-between'>
            <div className='invisible flex-1'>
              <span></span>
            </div>

            <div className='flex-1 flex justify-center'>
              <NavPages />
            </div>

            <div className='flex-1 flex justify-end items-center gap-4'>
              <ProjectSelector />
              <UserIcon />
            </div>
          </div>
        )
        : <></>}
    </div>
  )
}
