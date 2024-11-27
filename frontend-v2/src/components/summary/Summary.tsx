'use client'

import { getServerRequest } from '@/networking/server_requests'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { useState, useEffect } from 'react'

export function Summary() {
  const [summary, setSummary] = useState<RecordingsSummary | null>(null)

  useEffect(() => {
    fetchSummary().then((summary) => {
      if (!summary) {
        return
      }
      setSummary(summary)
    })
  }, [])
  return (
    <div className='flex flex-col justify-center items-center'>
      <div className='card bg-base-300 shadow-xl w-1/2 max-w-xl'>
        <div className='card-body'>
          <h3 className='card-title'>Recordings Summary</h3>
          <p>
            <strong>Number of Finished Possible Examples:</strong>{' '}
            {summary?.num_finished_possible_examples}
          </p>
          <p>
            <strong>Number of Labels:</strong> {summary?.num_labels}
          </p>
          <p>
            <strong>Number of Embeddings:</strong> {summary?.num_embeddings}
          </p>
          <p>
            <strong>Number of Source Files:</strong> {summary?.num_source_files}
          </p>
          <p>
            <strong>Hours of Recordings:</strong>{' '}
            {Math.round(summary?.hours_recordings ?? 0)}
          </p>
        </div>
      </div>
    </div>
  )
}

async function fetchSummary() {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    return
  }

  const res = await getServerRequest(
    `recordings_summary?project_id=${projectId}`
  )
  if (res.status === 200) {
    return (await res.json()) as RecordingsSummary
  }
  throw new Error('Failed to fetch summary')
}

export type RecordingsSummary = {
  num_finished_possible_examples: number
  num_labels: number
  num_embeddings: number
  num_source_files: number
  hours_recordings: number
}
