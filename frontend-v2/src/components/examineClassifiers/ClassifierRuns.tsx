'use client'

import { ClassifyRun } from '@/models/perch'
import { useEffect, useState } from 'react'
import { getCurrentProject } from '../navigation/ProjectSelector'
import {
  getServerRequest,
  postServerRequest,
} from '@/networking/server_requests'
import { SingleClassifyRun } from './SingleClassifyRun'

export function ClassifierRuns() {
  const [classifierRuns, setClassifierRuns] = useState<ClassifyRun[]>([])
  const [focusedRun, setFocusedRun] = useState<ClassifyRun>()
  const [message, setMessage] = useState<string>()

  console.log(classifierRuns)

  useEffect(() => {
    fetchClassifierRuns().then((runs) => setClassifierRuns(runs))
  }, [])

  if (!classifierRuns) {
    return (
      <div className='flex justify-center items-center align-middle'>
        <span className='loading loading-infinity loading-lg'></span>
      </div>
    )
  }

  return (
    <div className='flex justify-center items-center'>
      <div className='flex flex-col'>
        {/* TODO: make this button have a modal to make sure that the user wants to make classifier */}
        <button
          className='btn btn-primary p-2 m-4'
          onClick={async () => {
            const mess = await runClassifier()
            if (mess) {
              setMessage(mess)
            }
          }}
        >
          Make New Classifier
        </button>
        {message && <div className='text-green-400'> {message} </div>}
        {classifierRuns.map((run, i) => (
          <div key={i}>
            <button onClick={() => setFocusedRun(run)}>
              Date of Classifier: {run.datetime}
            </button>
          </div>
        ))}
      </div>
      {focusedRun && <SingleClassifyRun classifyRun={focusedRun} />}
    </div>
  )
}

export async function fetchClassifierRuns() {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('No project ID found')
  }
  const res = await getServerRequest(
    `get_classifier_runs?project_id=${projectId}`
  )
  if (res.status === 200) {
    const response = await res.json()
    if (response.message) {
      return []
    }
    return (await res.json()) as ClassifyRun[]
  }
  throw new Error('Failed to get classifier runs')
}

async function runClassifier() {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('No project ID found')
  }
  const res = await postServerRequest(`classify?project_id=${projectId}`, {})
  if (res.status === 200) {
    const response = await res.json()
    return response.message
  }
  throw new Error('failed to run classifier')
}
