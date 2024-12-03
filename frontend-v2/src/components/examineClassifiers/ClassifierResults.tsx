'use client'

import { useRouter } from 'next/navigation'
import { getServerRequest } from '@/networking/server_requests'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { ClassifiedResult } from '@/models/perch'
import { useEffect, useState } from 'react'
import { ClassifierSummary } from './ClassifierSummary'
import { fetchAnnotationSummary } from '../examineAnnotations/ExamineAnnotations'
import { SingleLabelClassifiedRecs } from './SingleLabelClassifiedRecs'

export function ClassifierResults({
  classifyRunId,
}: {
  classifyRunId: number
}) {
  const router = useRouter()
  const [classifierResults, setClassifierResults] = useState<
    ClassifiedResult[]
  >([])
  const [singleLabel, setSingleLabel] = useState<string | null>(null)
  const [annotationSummary, setAnnotationSummary] = useState<
    Record<string, number>
  >({})

  const filteredClassifierResults = singleLabel
    ? classifierResults.filter((result) => result.label === singleLabel)
    : classifierResults

  useEffect(() => {
    const projectId = getCurrentProject()?.id
    if (!projectId) {
      return
    }
    fetchAnnotationSummary(projectId).then((summary) => {
      setAnnotationSummary(summary)
    })
  }, [])

  useEffect(() => {
    fetchClassifierResults(classifyRunId).then((results) => {
      setClassifierResults(results)
    })
  }, [])

  return (
    <>
      <button
        onClick={() => router.back()}
        className='absolute top-6 left-10 btn btn-accent'
      >
        ← Back
      </button>
      <div className='flex gap-4'>
        <ClassifierSummary
          classifiedResults={classifierResults}
          singleLabel={singleLabel}
          setSingleLabel={setSingleLabel}
        />
        {singleLabel && (
          <SingleLabelClassifiedRecs
            classifiedResults={filteredClassifierResults}
            annotationSummary={annotationSummary}
          />
        )}
      </div>
    </>
  )
}

async function fetchClassifierResults(classifyRunId: number) {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('No project selected')
  }
  const res = await getServerRequest(
    `get_classifier_results?project_id=${projectId}&classifier_run_id=${classifyRunId}`
  )
  if (res.status === 200) {
    return await res.json()
  }
  throw new Error('Failed to fetch classifier results')
}
