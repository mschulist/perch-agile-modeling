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
