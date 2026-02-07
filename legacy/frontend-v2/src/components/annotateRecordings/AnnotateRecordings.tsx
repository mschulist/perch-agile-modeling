'use client'

import { PossibleExample } from '@/models/perch'
import { getUrl, postServerRequest } from '@/networking/server_requests'
import { useEffect, useState } from 'react'
import { getCurrentProject } from '../navigation/ProjectSelector'
import Image from 'next/image'
import { AnnotationButtons } from './AnnotationButtons'

export function AnnotateRecordings() {
  const [possibleExample, setPossibleExample] =
    useState<PossibleExample | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(false)

  function annotateAndGetNextPossibleExample(labels: string[]) {
    postAnnotation(possibleExample!.embedding_id, labels).then(() => {
      fetchNextPossibleExample(setMessage).then((possibleExample) => {
        setPossibleExample(possibleExample)
      })
    })
  }

  useEffect(() => {
    fetchNextPossibleExample(setMessage).then((possibleExample) => {
      setLoading(false)
      setPossibleExample(possibleExample)
    })
  }, [])

  return (
    <div className='flex flex-col items-center w-full pt-16'>
      {possibleExample && (
        <div className='card bg-base-300 shadow-xl w-1/2 max-w-xl'>
          <div className='card-body'>
            <h3 className='card-title'>Filename: {possibleExample.filename}</h3>
            <p>
              <strong>Possible Species:</strong>{' '}
              {possibleExample.target_species}
            </p>
            <p>
              <strong>Possible Call Type:</strong>{' '}
              {possibleExample.target_call_type}
            </p>
            <figure className='mt-4'>
              <Image
                src={getUrl(possibleExample.image_path)}
                width={500}
                height={600}
                alt='annotation'
                className='rounded-lg'
              />
            </figure>
            <div className='mt-4'>
              <audio
                controls
                src={getUrl(possibleExample.audio_path)}
                className='w-full'
                preload='none'
              />
            </div>
            <div className='card-actions justify-end mt-4'>
              <AnnotationButtons
                possibleExample={possibleExample}
                annotateAndGetNextPossibleExample={
                  annotateAndGetNextPossibleExample
                }
              />
            </div>
          </div>
        </div>
      )}
      {loading && <span className='loading loading-infinity loading-lg'></span>}
      {message && <p className='text-xl'>{message}</p>}
    </div>
  )
}

async function fetchNextPossibleExample(setMessage: (message: string) => void) {
  const projectId = getCurrentProject()?.id
  const res = await postServerRequest(
    `get_next_possible_example?project_id=${projectId}`,
    {}
  )
  if (res.status === 200) {
    const response = await res.json()
    if (
      'message' in response &&
      response.message === 'No more possible examples'
    ) {
      setMessage(response.message)
      return null
    }
    return response as PossibleExample
  } else {
    throw new Error('Failed to fetch next possible example')
  }
}

async function postAnnotation(embeddingId: number, labels: string[]) {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('No project selected')
  }
  const res = await postServerRequest(
    `annotate_example?project_id=${projectId}&embedding_id=${embeddingId}`,
    labels
  )
  if (res.status !== 200) {
    throw new Error('Failed to post annotation')
  }
}
