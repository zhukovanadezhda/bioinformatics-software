# Research of software development practices in the field of bioinformatics

[![Python 3.10.9](https://img.shields.io/badge/python-%E2%89%A5_3.10.9-blue.svg)](https://www.python.org/downloads/release/python-397/)
[![Conda 22.11.1](https://img.shields.io/badge/conda-%E2%89%A5_22.11.1-green.svg)](https://docs.conda.io/en/latest/miniconda.html)
[![GitHub last commit](https://img.shields.io/github/last-commit/zhukovanadezhda/bioinformatics-software.svg)](https://github.com/zhukovanadezhda/bioinformatics-software)
![GitHub stars](https://img.shields.io/github/stars/zhukovanadezhda/bioinformatics-software.svg?style=social)

# Setup your environment

Clone the repository:

```bash
git clone https://github.com/zhukovanadezhda/bioinformatics-software.git
```

Install [miniconda](https://docs.conda.io/en/latest/miniconda.html).

Install [mamba](https://github.com/mamba-org/mamba):

```bash
conda install mamba -n base -c conda-forge
```

Create the `bioinfosoft` conda environment:

```
mamba env create -f binder/environment.yml
```

Load the `bioinfosoft` conda environment:

```
conda activate bioinfosoft
```

Note: you can also update the conda environment with:

```bash
mamba env update -f binder/environment.yml
```

To deactivate an active environment, use

```
conda deactivate
```
