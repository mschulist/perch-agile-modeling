---
sidebar_position: 2
---

# Setup

## Overview

To initialize a directory, run the following command:

```bash
perch-analyzer init \
    --data_dir=<directory-for-data> \
    --project_name=<project_name> \
    --user_name=<your-name!> \
    --embedding_model=<model-of-choice>
```

This step creates a project at the given directory, which contains all files (except for the ARU data) used in the project.


## Models

This project is based on the Perch-Hoplite repository, so we support the following models:
- Perch
- Perch V2
- BirdNet

We recommend using the Perch V2 model.

## Usage 

Here is an example, using the `perch_v2` model (which is recommended):

```bash
perch-analyzer init \
    --data_dir=<data-directory> \
    --project_name=<your-project-name> \
    --user_name=<your-name> \
    --embedding_model=perch_v2
```

- `data_dir` is the directory used to [setup](setup) a project. 