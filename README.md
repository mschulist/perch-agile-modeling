# Perch Agile Modeling

# Goal

The goal of this project is to be able to classify large batches of ARU recordings using transfer learning, all in the cloud. The [Perch framework](https://github.com/google-research/perch) is an incredible took for bird vocalization classifiation and works very well due to the fact that the final training is done on the same recordings that you want to classify. 

# Agile Modeling Workflow

- Compute the embeddings for all of your ARU recordings. All we need from you is a (glob) path to a public google storage bucket containing your ARU recordings. Example: `gs://chirp-public-bucket/soundscapes/high_sierras/audio/*`.
- While the embeddings are being computed (which may take a while, depending on the number of recordings), you can gather "target recordings" for the species of interest. These recordings are used to gather examples of each species from the ARU recordings. Normally, these are from xeno-canto.
- Once the embeddings are computed, you can search the ARU recordings for the species of interest. This might also take a while, although less time than computing the embeddings.
- Finally, you can go through the search results and annotate the recordings. The goal of this step is to gather examples from the ARU data that contain the species of interest. We can split the species into song/call (or any other subclass), which the classifier will be able to distinguish with enough annotated examples. There is not a perfect number of examples for each class, but 10-20 seems to work well. We will call the annotated recordings "labeled outputs."
- Train a classifier on the labeled outputs. Using this classifier (which is a single linear map from the embeddings to the output layer containing the classification), classify all of the recordings.

