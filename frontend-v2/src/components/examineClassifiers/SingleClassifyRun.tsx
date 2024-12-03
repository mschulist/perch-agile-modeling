'use client'

import { ClassifyRun } from '@/models/perch'
import { SearchClassifier } from './SearchClassifier'
import { use, useEffect, useState } from 'react'
import { fetchAnnotationSummary } from '../examineAnnotations/ExamineAnnotations'
import { getCurrentProject } from '../navigation/ProjectSelector'

export function SingleClassifyRun({
  classifyRun,
}: {
  classifyRun: ClassifyRun
}) {
  const [classifierLabels, setClassifierLabels] = useState<string[]>([])
  const metrics = classifyRun.eval_metrics

  useEffect(() => {
    const projectId = getCurrentProject()?.id
    if (projectId) {
      // TODO: make this fetch the actual labels from the classifier
      // instead of the annotation summary (wait for new Perch update...)
      fetchAnnotationSummary(projectId).then((summary) => {
        setClassifierLabels(Object.keys(summary))
      })
    }
  }, [])

  return (
    <div className='flex flex-col justify-center'>
      <h2 className='text-xl font-bold mb-4'>
        Classifier Run: {classifyRun.datetime}
      </h2>
      <div>Top 1 Accuracy: {metrics.top1_acc}</div>
      <div>ROC AUC: {metrics.roc_auc}</div>
      <div>CMAP: {metrics.cmap}</div>
      <div className='mt-4'>
        <SearchClassifier
          classifiedDateTime={classifyRun.datetime}
          classifierLabels={classifierLabels}
        />
      </div>
    </div>
  )
}
