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

## Example 

Here is an example, using the `perch_v2` model (which is recommended):

```bash
perch-analyzer init \
    --data_dir=caples_data \
    --project_name=caples \
    --user_name=mark \
    --embedding_model=perch_v2
```
