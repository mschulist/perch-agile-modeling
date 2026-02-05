---
sidebar_position: 3
---

# Embedding

The first step in the agile modeling process is to embed your data. 

## Embedding Rationale

Each [window](terminology) is itself an extremely high-dimensional object, however we would like to make sense of the properties of the birds vocalizing in the given window. Do to this, we use an embedding model. An embedding model takes a window as input and outputs a vector in $\mathbb{R}^n$, where $n$ is embedding dimension.

Let $e_1$ and $e_2$ be two embeddings for a given species (say Blue Jay). Then, we denote the _distance_ between $e_1$ and $e_2$ by $d(e_1, e_2)$. This distance is a metric that gives us a notion of similarity between embeddings. We usually use the inner product $\langle \cdot, \cdot \rangle$ for this metric[^1], however there are other metrics we can use, such as the Euclidian distance. 

Given that $e_1$ and $e_2$ both contain the same focal species, we expect their inner product $\langle e_1, e_2 \rangle$ to be high. Say that $e_3$ is an embedding for another species, such as Great-horned Owl. Then we expect $\langle e_1, e_3 \rangle$ and $\langle e_2, e_3 \rangle$ to be small, because these embeddings come from different focal species. 

Thankfully for us, the hard work of creating these embedding models has already been done for us! So all we need to do is run these embedding models on our data, making our task of creating a classifier far easier (and computationally cheap). 

## Example

To embed your data, we use the following command:

```bash
perch-analyzer embed \
    --data_dir=<data-directory> \
    --ARU_base_path=<base_path> \
    --ARU_file_glob=<file_glob>
```

- `data_dir` is the directory used to [setup](setup) a project.  
- `ARU_base_path` is the base path of the ARU recordings. Ideally, this path is an absolute path such as `/home/mschulist/birds/caples_sound`
- `ARU_file_glob` is the file glob used to identify ARU recordings within the `ARU_base_path`. If my files were in `/home/mschulist/birds/caples_sound/*.wav`, then I would set `ARU_file_glob="*.wav"`. Note the addition of the quotations around `".wav"`. This ensures that the command line does not automatically expand out the file glob and match all files with the given glob.


[^1]: Note that the inner product is technically not a metric (in the mathematical sense) because the inner product can be negative.