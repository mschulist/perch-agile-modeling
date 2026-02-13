---
sidebar_position: 2
---

# Setup

This step creates a project at the given directory, which contains all files (except for the ARU data) used in the project.


## Models

This project is based on the Perch-Hoplite repository, so we support the following models:
- [Perch](https://doi.org/10.48550/arXiv.2307.06292)
- [Perch V2](https://doi.org/10.48550/arXiv.2508.04665)
- [BirdNet](https://doi.org/10.1016/j.ecoinf.2021.101236)

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