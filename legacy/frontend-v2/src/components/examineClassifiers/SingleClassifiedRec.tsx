import { ClassifiedResult } from '@/models/perch'
import { getUrl } from '@/networking/server_requests'
import { useState, useEffect } from 'react'
import { MultiSelect } from '../examineAnnotations/MultiSelect'
import { postNewLabels } from '../examineAnnotations/SingleAnnotation'
import Image from 'next/image'

export function SingleClassifiedRecording({
  classifiedResult,
  annotationSummary,
}: {
  classifiedResult: ClassifiedResult
  annotationSummary: Record<string, number>
}) {
  const [annotatedLabels, setAnnotatedLabels] = useState(
    classifiedResult.annotated_labels
  )
  const [newAnnotatedLabels, setNewAnnotatedLabels] =
    useState<string[]>(annotatedLabels)
  const [editingLabels, setEditingLabels] = useState(false)

  useEffect(() => {
    setAnnotatedLabels(classifiedResult.annotated_labels)
    setNewAnnotatedLabels(classifiedResult.annotated_labels)
  }, [classifiedResult.annotated_labels])

  function handleLabelSave() {
    if (newAnnotatedLabels === annotatedLabels) {
      return
    }
    postNewLabels(classifiedResult.embedding_id, newAnnotatedLabels)
      .then(() => {
        setAnnotatedLabels(newAnnotatedLabels)
      })
      .catch((e) => {
        console.error(e)
      })
  }

  return (
    <li
      key={classifiedResult.filename}
      className={`card shadow-xl compact bg-base-300 p-2 m-4`}
    >
      <div className='card-body'>
        <h2 className='card-title'>{classifiedResult.filename}</h2>
        <div className='text-base text-gray-400'>
          Logit: {classifiedResult.logit}
        </div>
        <div className='text-base text-gray-400'>
          Classifier Label: {classifiedResult.label}
        </div>
        <button
          type='button'
          className={`btn btn-xs ${editingLabels ? 'btn-secondary' : 'btn-primary'} w-32`}
          onClick={() => {
            if (editingLabels) {
              handleLabelSave()
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
                setLabels={setNewAnnotatedLabels}
                labels={newAnnotatedLabels}
                placeholder='New labels...'
              />
            </>
          ) : (
            `Annotated labels: ${annotatedLabels}`
          )}
        </div>
        <figure>
          <Image
            src={getUrl(classifiedResult.image_path)}
            width={550}
            height={450}
            alt='annotation'
            className='rounded-xl'
          />
        </figure>
        <audio
          controls
          src={getUrl(classifiedResult.audio_path)}
          className='mt-4 w-full'
          preload='none'
        />
      </div>
    </li>
  )
}
