'use client'

import { ClassifyRun } from '@/models/perch'
import { SearchClassifier } from './SearchClassifier'
import { useRouter } from 'next/navigation'

export function SingleClassifyRun({
  classifyRun,
}: {
  classifyRun: ClassifyRun
}) {
  const metrics = classifyRun.eval_metrics
  const classifierLabels = classifyRun.classes

  const router = useRouter()

  function handleExamineClassifierResults() {
    router.push(`/classify/classify-results/${classifyRun.id}`)
  }

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
      <button
        className='my-10 btn btn-accent'
        onClick={handleExamineClassifierResults}
      >
        Examine Classifier Results
      </button>
    </div>
  )
}
