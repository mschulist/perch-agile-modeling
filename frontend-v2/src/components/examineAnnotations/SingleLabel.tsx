'use client'

import { getServerRequest } from '@/networking/server_requests'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { useEffect, useState } from 'react'
import { AnnotatedRecording } from '@/models/perch'
import { SingleAnnotation } from './SingleAnnotation'

export function SingleLabel({
  label,
  annotationSummary,
}: {
  label: string
  annotationSummary: Record<string, number>
}) {
  const [annotations, setAnnotations] = useState<AnnotatedRecording[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSingleLabel(label).then((singleLabel) => {
      console.log(singleLabel)
      setAnnotations(singleLabel)
      setLoading(false)
    })
  }, [label])

  return (
    <div className='flex flex-col w-full items-center'>
      <h2 className='text-3xl'>{label}</h2>
      {loading && <span className='loading loading-infinity loading-lg'></span>}
      <ul>
        {annotations.map((annotation, i) => (
          <SingleAnnotation
            key={i}
            annotation={annotation}
            annotationSummary={annotationSummary}
          />
        ))}
      </ul>
    </div>
  )
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
