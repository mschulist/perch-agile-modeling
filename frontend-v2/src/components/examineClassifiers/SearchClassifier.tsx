'use client'

import { postServerRequest } from '@/networking/server_requests'
import { use, useEffect, useState } from 'react'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { MultiSelect } from '../examineAnnotations/MultiSelect'
import { LogitRangeSlider } from './LogitRangeSlider'

type SearchClassifierProps = {
  classifiedDateTime: string
  classifierLabels: string[]
}

export function SearchClassifier(props: SearchClassifierProps) {
  const [maxLogit, setMaxLogit] = useState<boolean>(true)
  const [logitRanges, setLogitRanges] = useState<Array<[number, number]>>([
    [0, 2],
  ])
  const [numPerRange, setNumPerRange] = useState<number>(4)
  const [labels, setLabels] = useState<string[]>([])
  const [message, setMessage] = useState<string>()

  async function handleSearchButton() {
    try {
      const message = await postSearchClassifier(
        maxLogit,
        logitRanges,
        numPerRange,
        labels,
        props.classifiedDateTime
      )
      setMessage(message)
    } catch (e: any) {
      setMessage("Couldn't search classifier")
    }
  }

  return (
    <div className='flex flex-col gap-3'>
      <h3 className='text-lg font-bold mb-2'>Search Classifier</h3>
      <div className='flex gap-2'>
        <label className='mb-1'>Max Logit</label>
        <input
          type='checkbox'
          className='checkbox'
          checked={maxLogit}
          onChange={(e) => setMaxLogit(e.target.checked)}
        />
      </div>
      <div className='flex flex-col'>
        <label className='mb-5'>Logit Ranges</label>
        <LogitRangeSlider
          logitRanges={logitRanges}
          setLogitRanges={setLogitRanges}
        />
      </div>
      <div className='flex flex-col'>
        <label className='mb-1'>Num Per Range</label>
        <input
          type='number'
          value={numPerRange}
          className='input input-bordered w-24'
          onChange={(e) => {
            const value = Math.min(Math.max(1, parseInt(e.target.value)), 15)
            setNumPerRange(isNaN(value) ? 1 : value)
          }}
        />
      </div>
      <div className='flex flex-col w-72'>
        <label>Labels</label>
        <MultiSelect
          options={props.classifierLabels}
          labels={labels}
          setLabels={setLabels}
          placeholder='Select labels'
          required={false}
        />
      </div>
      <button className='btn btn-secondary' onClick={handleSearchButton}>
        Search Classifier
      </button>
    </div>
  )
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
    `search_classified?project_id=${projectId}&classified_datetime=${datetime}&max_logits=${maxLogit}&num_per_range=${numPerRange}`,
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
