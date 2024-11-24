'use client'

import { useEffect, useState } from 'react'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { getServerRequest } from '@/networking/server_requests'
import { AnnotationSummary } from './AnnotationSummary'
import { SingleLabel } from './SingleLabel'

export function ExamineAnnotations() {
  const [annotationSummary, setAnnotationSummary] = useState<
    Record<string, number>
  >({})
  const [singleLabel, setSingleLabel] = useState<string | null>(null)

  useEffect(() => {
    const projectId = getCurrentProject()?.id
    if (!projectId) {
      return
    }
    fetchAnnotationSummary(projectId).then((summary) => {
      console.log(summary)
      setAnnotationSummary(summary)
    })
  }, [])

  function refreshAnnotationSummary() {
    const projectId = getCurrentProject()?.id
    if (!projectId) {
      return
    }
    fetchAnnotationSummary(projectId).then((summary) => {
      setAnnotationSummary(summary)
    })
  }

  return (
    <div className='flex flex-row w-full justify-evenly'>
      <AnnotationSummary
        annotationSummary={annotationSummary}
        setSingleLabel={setSingleLabel}
      />
      {singleLabel != null && (
        <SingleLabel
          label={singleLabel}
          annotationSummary={annotationSummary}
          refreshAnnotationSummary={refreshAnnotationSummary}
        />
      )}
    </div>
  )
}

export async function fetchAnnotationSummary(project_id: number) {
  const res = await getServerRequest(
    `get_label_summary?project_id=${project_id}`
  )
  if (res.status === 200) {
    return res.json()
  } else {
    throw new Error('Failed to fetch annotation summary')
  }
}
