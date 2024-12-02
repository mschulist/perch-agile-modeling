import { ClassifyRun } from '@/models/perch'

export function SingleClassifyRun({
  classifyRun,
}: {
  classifyRun: ClassifyRun
}) {
  const metrics = classifyRun.eval_metrics
  return (
    <div className='flex flex-col justify-center items-center'>
      <div>Top 1 Accuracy: {metrics.top1_acc}</div>
      <div>ROC AUC: {metrics.roc_auc}</div>
      <div>CMAP: {metrics.cmap}</div>
      {/* TODO: Make these collapsible */}
      <div>
        ROC AUC by label
        {metrics.roc_auc_individual.map((rocauc, i) => (
          <div key={i}>
            {metrics.eval_labels[i]}: {rocauc}
          </div>
        ))}
      </div>
      <div>
        CMAP by label
        {metrics.cmap_individual.map((cmap, i) => (
          <div key={i}>
            {metrics.eval_labels[i]}: {cmap}
          </div>
        ))}
      </div>
    </div>
  )
}
