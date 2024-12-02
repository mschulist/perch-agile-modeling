export type AnnotatedRecording = {
  filename: string
  timestamp_s: number
  species_labels: string[]
  embedding_id: number
  image_path: string
  audio_path: string
}

export type PossibleExample = {
  embedding_id: number
  filename: string
  timestamp_s: number
  score: number
  image_path: string
  audio_path: string
  target_species: string
  target_call_type: string
}

export type ClassifyRun = {
  id: number
  datetime: string
  project_id: number
  eval_metrics: EvalMetrics
}

export type EvalMetrics = {
  top1_acc: number
  roc_auc: number
  roc_auc_individual: number[]
  cmap: number
  cmap_individual: number[]
}

export type ClassifiedResult = {
  id: number
  filename: string
  timestamp_s: number
  logit: number
  embedding_id: number
  label: string
  project_id: number
  classifier_run_id: number
  image_path: string
  audio_path: string
  annotated_labels: string[]
}
