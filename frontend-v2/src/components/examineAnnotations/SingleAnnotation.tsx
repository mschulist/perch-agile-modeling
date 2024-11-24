'use client'

import { AnnotatedRecording } from '@/models/perch'
import { getUrl, postServerRequest } from '@/networking/server_requests'
import { use, useEffect, useState } from 'react'
import Image from 'next/image'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { MultiSelect } from './MultiSelect'

export function SingleAnnotation({
  annotation,
  annotationSummary,
  refreshAnnotationSummary,
}: {
  annotation: AnnotatedRecording
  annotationSummary: Record<string, number>
  refreshAnnotationSummary: () => void
}) {
  // TODO: make a nice drop down for selecting labels
  const [strLabels, setStrLabels] = useState(
    annotation.species_labels.join(',')
  )
  const [editingLabels, setEditingLabels] = useState(false)

  useEffect(() => {
    setStrLabels(annotation.species_labels.join(','))
  }, [annotation.species_labels])

  return (
    <li
      key={annotation.filename}
      className='card shadow-xl compact bg-base-300 p-2 m-4'
    >
      <div className='card-body'>
        <h2 className='card-title'>{annotation.filename}</h2>
        <button
          className={`btn btn-xs ${editingLabels ? 'btn-secondary' : 'btn-primary'} w-32`}
          onClick={() => {
            if (editingLabels) {
              postNewLabels(annotation.embedding_id, strLabels.split(','))
                .then(() => {
                  refreshAnnotationSummary()
                })
                .catch((e) => {
                  console.error(e)
                })
            }
            setEditingLabels(!editingLabels)
          }}
        >
          {editingLabels ? 'Save' : 'Change Labels'}
        </button>
        <div className='text-sm text-gray-400'>
          {editingLabels ? (
            <>
              New labels:
              <MultiSelect
                options={Object.keys(annotationSummary)}
                setStrLabels={setStrLabels}
                strLabels={strLabels}
              />
            </>
          ) : (
            `Labels: ${strLabels}`
          )}
        </div>
        <figure>
          <Image
            src={getUrl(annotation.image_path)}
            width={450}
            height={550}
            alt='annotation'
            className='rounded-xl'
          />
        </figure>
        <audio
          controls
          src={getUrl(annotation.audio_path)}
          className='mt-4 w-full'
          preload='none'
        />
      </div>
    </li>
  )
}

async function postNewLabels(embedding_id: number, labels: string[]) {
  console.log('posting new labels', embedding_id, labels)
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    console.error('No project selected')
    return
  }
  const res = await postServerRequest(
    `relabel_example?project_id=${projectId}&embedding_id=${embedding_id}`,
    labels
  )
  if (res.status === 200) {
    return res.json()
  } else {
    console.error('Failed to post new labels')
    return
  }
}
