'use client'

import { getServerRequest } from '@/networking/server_requests'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { useEffect, useState } from 'react'
import { AnnotatedRecording } from '@/models/perch'

export function SingleLabel({ label }: { label: string }) {
  const [annotations, setAnnotations] = useState<AnnotatedRecording[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSingleLabel(label).then((singleLabel) => {
      setAnnotations(singleLabel)
      setLoading(false)
    })
  }, [label])

  return (
    <div className='flex flex-col w-full items-center'>
      <h2 className='text-3xl'>Single Label</h2>
      {loading && <span className='loading loading-infinity loading-lg'></span>}
      <ul>
        {annotations.map((annotation) => (
          <li key={annotation.filename}>
            <p>Filename: {annotation.filename}</p>
            <p>Offset: {annotation.timestamp_s} seconds</p>
            <p>Labels: {annotation.species_labels.join(', ')}</p>
            <img src={getUrl(annotation.image_path)} alt='annotation' />
            <audio controls src={getUrl(annotation.audio_path)}></audio>
          </li>
        ))}
      </ul>
    </div>
  )
}

// TODO: make sure this is the correct server URL and check that it is not
// already a gs url (then we would not want to prepend the server URL)
function getUrl(path: string) {
  const serverUrl = process.env.SERVER_URL || 'http://localhost:8000'
  if (path.startsWith('gs://')) {
    return path
  }
  return `${serverUrl}/get_file?filename=${path}`
}

async function getSingleLabel(label: string) {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    return
  }
  return fetchSingleLabel(projectId, label)
}

async function fetchSingleLabel(project_id: number, label: string) {
  const res = await getServerRequest(
    `get_annotations_by_label?project_id=${project_id}&label=${label}`
  )
  if (res.status === 200) {
    return res.json()
  } else {
    throw new Error('Failed to fetch single label')
  }
}
