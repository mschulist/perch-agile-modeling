import { ClassifyRun } from '@/models/perch'

export function SingleClassifyRun({
  classifyRun,
}: {
  classifyRun: ClassifyRun
}) {
  const metrics = classifyRun.eval_metrics
  return (
    <div className='flex flex-col justify-center'>
      <h2 className='text-xl font-bold mb-4'>
        Classifier Run: {classifyRun.datetime}
      </h2>
      <div>Top 1 Accuracy: {metrics.top1_acc}</div>
      <div>ROC AUC: {metrics.roc_auc}</div>
      <div>CMAP: {metrics.cmap}</div>
    </div>
  )
}
