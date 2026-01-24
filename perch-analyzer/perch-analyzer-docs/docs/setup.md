---
sidebar_position: 2
---

# Setup

To initialize a directory, run the following command:

```bash
perch-analyzer init \
    --data_dir=<directory-for-data> \
    --project_name=<project_name> \
    --user_name=<your-name!> \
    --embedding_model=<model-of-choice>
```

Here is an example, using the `perch_v2` model (which is recommended):

```bash
perch-analyzer init \
    --data_dir=caples_data \
    --project_name=caples \
    --user_name=mark \
    --embedding_model=perch_v2
```

This initializes the directory that will hold all of the databases and configuration used throughout the agile modeling process. The only data not in this directory is the ARU data. 