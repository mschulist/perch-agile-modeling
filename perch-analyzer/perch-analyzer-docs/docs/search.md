---
sidebar_position: 5
---

# Search

Searching allows you to efficiently find [similar](embedding#embedding-rationale) recordings in your project. In the [previous step](target_recordings), we gathered target recordings for our focal species.

With our target recordings in hand, we can search for ARU windows that are similar to our target recordings. Given that these found windows are similar to recordings of our focal species, we have a high likelihood that the similar windows contain the same focal species. Hence, we are able to quickly search for particular species in our ARU dataset and mark them as [possible examples](terminology). 

After searching, all target recordings will be marked as _finished_ to prevent searching the ARU windows with the same target recordings over and over. If you want to search for more recordings, gather more target recordings and then try searching again. 

## Usage

To search, use the following command:

```bash
perch-analyzer search \ 
    --data_dir=<data-directory> \
    --num_per_target_recording=<number>
```

- `data_dir` is the directory used to [setup](setup) a project.  
- `num_per_target_recording` is the number of windows

