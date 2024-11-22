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

  return (
    <div className='flex flex-row w-full'>
      <div className='flex flex-col w-full items-center'>
        <h2 className='text-3xl'>Annotation Summary</h2>
        <AnnotationSummary
          annotationSummary={annotationSummary}
          setSingleLabel={setSingleLabel}
        />
      </div>
      {singleLabel && <SingleLabel label={singleLabel} annotationSummary={annotationSummary}/>}
    </div>
  )
}

async function fetchAnnotationSummary(project_id: number) {
  const res = await getServerRequest(
    `get_label_summary?project_id=${project_id}`
  )
  if (res.status === 200) {
    return res.json()
  } else {
    throw new Error('Failed to fetch annotation summary')
  }
}
