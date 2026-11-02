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
- `user_name` is the name the command line tools record you as. In the GUI,
  annotations are credited to whoever is signed in.

## Logins

The GUI asks everyone to sign in, so several people can annotate the same
project at once and each person's labels are recorded under their own name.
There are no roles: every account can do everything.

Create an account for each annotator:

```bash
perch-analyzer add_user --data_dir=<data-directory> --username=<name>
```

You will be asked for the password twice. Pass `--password=<password>` to set it
without a prompt, though it will then end up in your shell history.

The other account commands are:

- `perch-analyzer list_users --data_dir=<data-directory>` lists the accounts.
- `perch-analyzer set_password --data_dir=<data-directory> --username=<name>`
  resets a password. People can also change their own from the `Account` page
  in the GUI.
- `perch-analyzer remove_user --data_dir=<data-directory> --username=<name>`
  deletes an account. Annotations it made are kept, and anyone signed in as
  that user is sent back to the login page.

If a project has no accounts yet, the GUI's login page offers to create the
first one instead.

To let others reach the GUI over your network, start it with `--host 0.0.0.0`
(see [Annotate](annotate)). The passwords are stored as salted hashes, but the
GUI is served over plain HTTP. Only expose it on a network you trust.