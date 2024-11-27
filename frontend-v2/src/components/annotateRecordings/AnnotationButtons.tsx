import { PossibleExample } from '@/models/perch'
import { useEffect, useState } from 'react'
import { MultiSelect } from '../examineAnnotations/MultiSelect'
import { fetchAnnotationSummary } from '../examineAnnotations/ExamineAnnotations'
import { getCurrentProject } from '../navigation/ProjectSelector'

export function AnnotationButtons({
  possibleExample,
  annotateAndGetNextPossibleExample,
}: {
  possibleExample: PossibleExample
  annotateAndGetNextPossibleExample: (labels: string[]) => void
}) {
  const [labels, setLabels] = useState<string[]>([])
  const [summaryLabels, setSummaryLabels] = useState<string[]>([])

  useEffect(() => {
    const projectId = getCurrentProject()?.id
    if (!projectId) {
      return
    }
    fetchAnnotationSummary(projectId).then((labels) => {
      setSummaryLabels(Object.keys(labels))
    })
  }, [])

  return (
    <div className='flex flex-col w-full justify-center items-center gap-6'>
      <MultiSelect
        options={summaryLabels}
        setLabels={setLabels}
        labels={labels}
        placeholder={`${possibleExample.target_species}_${possibleExample.target_call_type}`}
        required={false}
      />
      <button
        className='btn btn-primary w-44'
        disabled={labels.length === 0}
        onClick={() => {
          annotateAndGetNextPossibleExample(labels)
          setLabels([])
        }}
      >
        Annotate with Labels
      </button>
    </div>
  )
}
