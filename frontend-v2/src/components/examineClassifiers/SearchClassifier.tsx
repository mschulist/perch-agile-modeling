'use client'

import { postServerRequest } from '@/networking/server_requests'
import { useState } from 'react'
import { getCurrentProject } from '../navigation/ProjectSelector'

type SearchClassifierProps = {
  classifiedDateTime: string
}

export function SearchClassifier(props: SearchClassifierProps) {
  const [maxLogit, setMaxLogit] = useState<boolean>(true)
  const [logitRanges, setLogitRanges] = useState<number[][]>([[0, 2]])
  const [numPerRange, setNumPerRange] = useState<number>(4)
  const [labels, setLabels] = useState<string[]>([])
}

async function postSearchClassifier(
  maxLogit: boolean,
  logitRanges: number[][],
  numPerRange: number,
  labels: string[],
  datetime: string
) {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('Project ID not found')
  }
  const res = await postServerRequest(
    `search_classified?project_id=${projectId}&classified_datetime${datetime}&max_logits=${maxLogit}&num_per_range=${numPerRange}`,
    {
      labels,
      logit_ranges: logitRanges,
    }
  )
  if (res.status === 200) {
    const response = await res.json()
    return response.message
  }
  throw new Error('Failed to search classifier')
}
