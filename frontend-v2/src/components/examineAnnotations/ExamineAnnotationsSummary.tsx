'use client'

import { getServerRequest } from '@/networking/server_requests'
import { useState, useEffect } from 'react'
import { AnnotationSummary } from './AnnotationSummary'
import { getCurrentProject } from '../navigation/ProjectSelector'

export function ExamineAnnotationsSummary() {
  const [annotationSummary, setAnnotationSummary] = useState<{}>([])

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

  return <AnnotationSummary annotationSummary={annotationSummary} />
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
