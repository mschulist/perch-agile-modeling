'use client'

import { getServerRequest } from '@/networking/server_requests'
import { useEffect, useState } from 'react'

export const CURRENT_PROJECT_KEY = 'current_project'

export function ProjectSelector() {
  const [projects, setProjects] = useState<Project[]>([])
  const [currentProject, setCurrentProject] = useState<Project | null>(null)

  useEffect(() => {
    fetchProjects().then((projects) => setProjects(projects))
    setCurrentProject(getCurrentProject())
  }, [])

  return (
    <div className="dropdown">
      <div tabIndex={0} role="button" className="btn m-1">
        Current Project: {currentProject?.name}
      </div>
      <ul
        tabIndex={0}
        className="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow"
      >
        {projects.map((project) => (
          <li key={project.id}>
            <a
              onClick={() => {
                setProject(project)
                setCurrentProject(getCurrentProject())
              }}
            >
              {project.name}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

export type Project = {
  name: string
  id: number
}

function getCurrentProject(): Project | null {
  const project = localStorage.getItem(CURRENT_PROJECT_KEY)
  return project ? JSON.parse(project) : null
}

function setProject(project: Project) {
  localStorage.setItem(CURRENT_PROJECT_KEY, JSON.stringify(project))
}

async function fetchProjects() {
  const response = await getServerRequest('my_projects')
  if (response.ok) {
    return response.json()
  }
  throw new Error('Failed to fetch projects')
}
