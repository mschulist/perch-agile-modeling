---
sidebar_position: 4
---

# Target Recordings

Target recordings allow us to search for focal species in our dataset. Target recordings are known recordings of a focal species. 

Now that we have embedded our recordings, our goal is to annotate a subset of the windows with the species of interest (denoted _focal species_). 

One method to annotate recordings to do manually go through individual recordings and label all vocalizations. While this method is effective, we are far more likely to annotate common species than uncommon species. Similarly, rare species will be incredibly hard to annotate. 

Gathering target recordings is the first of two steps in our accelerated annotating process, allowing us to overcome the problems of annotating entire recordings.

## Xeno-canto

[Xeno-canto](https://xeno-canto.org/) is an online repository of wildlife sounds available to the public. Using this database, we can download recordings of our focal species. 

Xeno-canto recordings are _weakly labeled_, meaning we do not know exactly where in the recording the species is vocalizing (recordings are usually longer than the period where the bird is vocalizing). We use a technique to detect the location with the most activity in the recording to extract a window from the recording, equal to the window size specified by the chosen embedding model. 

## Custom

In addition to gathering target recordings from Xeno-canto, you can also import your own target recordings. We will take the first few seconds of the recording (equal to the window size for the chosen embedding model) and store the target recording.

## Usage

To gather target recordings from Xeno-canto, you first need to obtain a Xeno-canto API key from https://xeno-canto.org/explore/api (they key is on your account page). To set your Xeno-canto API key, use the following command:

```bash
TODO!
```

Then, you can use the following command to gather target recordings for a focal species:

```bash
perch-analyzer target_recordings \
    --data_dir=<data-directory> \
    --ebird_code=<6-letter-eBird-code> \
    --call_type=<song, call> \
    --num_recordings=<number-of-recordings>
```

- `data_dir` is the directory used to [setup](setup) a project. 
- `ebird_code` is the 6 letter eBird code of the species you want to gather target recordings for.
- `call_type` further filters the Xeno-canto recordings to be either `song` or `call`. 
- `num_recordings` is the number of recordings for the given `ebird_code` and `call_type` you want to gather.

