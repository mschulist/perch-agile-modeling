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
    <div className='flex justify-evenly'>
      <div className='flex flex-col'>
        <button
          className='btn btn-primary p-2 m-4'
          onClick={() => {
            ;(
              document.getElementById('my_modal_1') as HTMLDialogElement
            )?.showModal()
          }}
        >
          Make New Classifier
        </button>
        {message && <div className='text-green-400'> {message} </div>}
        {classifierRuns.map((run, i) => (
          <div
            key={i}
            className='m-2 transition-transform duration-200 ease-in-out transform hover:scale-110 hover:text-blue-500'
          >
            <button onClick={() => setFocusedRun(run)}>
              Date of Classifier: {run.datetime}
            </button>
          </div>
        ))}
      </div>
      {focusedRun && <SingleClassifyRun classifyRun={focusedRun} />}
      <dialog id='my_modal_1' className='modal'>
        <div className='modal-box'>
          <h3 className='font-bold text-lg'>Confirm Action</h3>
          <p className='py-4'>
            Are you sure you want to create a new classifier?
          </p>
          <div className='modal-action'>
            <form method='dialog'>
              <button className='btn'>Cancel</button>
            </form>
            <button
              className='btn btn-primary'
              onClick={async () => {
                const mess = await runClassifier()
                if (mess) {
                  setMessage(mess)
                }
                ;(
                  document.getElementById('my_modal_1') as HTMLDialogElement
                )?.close()
              }}
            >
              Confirm
            </button>
          </div>
        </div>
      </dialog>
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
    return response as ClassifyRun[]
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
