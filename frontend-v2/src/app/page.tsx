import { AgileStep } from '@/components/home/AgileStep'

export default function Home() {
  const step1Description = (
    <>
      <div className='text-gray-500 text-sm italic'>Coming soon...</div>
      Provide a path to your ARU recordings in a public Google Storage bucket.
      <code className='block mt-2 p-2 bg-gray-700 rounded text-sm'>
        gs://chirp-public-bucket/soundscapes/high_sierras/audio/*
      </code>
    </>
  )
  return (
    <div className='min-h-screen bg-primary-content'>
      {/* Header Section */}
      <header className='bg-primary-foreground shadow-sm'>
        <div className='max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8'>
          <h1 className='text-3xl font-bold text-primary'>
            Bird Vocalization Classification
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className='max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8 bg-primary-content'>
        <h2 className='text-2xl font-semibold mb-8'>Agile Modeling Workflow</h2>

        <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-3'>
          <AgileStep
            number={1}
            title='Compute Embeddings'
            description={step1Description}
          />

          <AgileStep
            number={2}
            title='Search Recordings'
            description='Search through ARU recordings for species of interest using the computed embeddings. Provide a list of 6-letter eBird codes and let the app use Xenocanto recordings to search for similar recordings from your data set.'
          />

          {/* Step 3 */}
          <AgileStep
            number={3}
            title='Annotate Recordings'
            description='Review and annotate 10-20 examples per class, distinguishing between song/call types.'
          />

          {/* Step 4 */}
          <AgileStep
            number={4}
            title='Train & Classify'
            description='Train a classifier on labeled outputs and use it to classify all recordings.'
          />

          {/* Step 5 */}
          <AgileStep
            number={5}
            title='Examine Classifier Outputs'
            description='Review the outputs from the classifier and label any misclassifications.'
          />
        </div>
      </main>
    </div>
  )
}
