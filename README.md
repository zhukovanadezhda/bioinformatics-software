# Research of Current Trends in Bioinformatics Software Development and Archiving


Software plays a vital role in modern scientific research, making it imperative to uphold both the accessibility and high quality of scientific software. Recognizing the significance of sustainable and reproducible science, Software Heritage (https://www.softwareheritage.org/) serves as a global archive for software preservation. This project focuses on examining the current trends in the development of bioinformatic software by gathering information from the abstracts of articles published on PubMed (https://pubmed.ncbi.nlm.nih.gov/). By utilizing the APIs of PubMed, GitHub, and Software Heritage, we collect diverse information regarding approximately 10,000 scientific software packages. Subsequently, our analysis aims to determine the proportion of archived software, assess the developmental dynamics, and evaluate the accessibility of software through the provided publication links.

[![Python 3.10.9](https://img.shields.io/badge/python-%E2%89%A5_3.10.9-blue.svg)](https://www.python.org/downloads/release/python-397/)
[![Conda 22.11.1](https://img.shields.io/badge/conda-%E2%89%A5_22.11.1-green.svg)](https://docs.conda.io/en/latest/miniconda.html)
[![GitHub last commit](https://img.shields.io/github/last-commit/zhukovanadezhda/bioinformatics-software.svg)](https://github.com/zhukovanadezhda/bioinformatics-software)
![GitHub stars](https://img.shields.io/github/stars/zhukovanadezhda/bioinformatics-software.svg?style=social)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/zhukovanadezhda/bioinformatics-software/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/zhukovanadezhda/bioinformatics-software)

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


# Dependency tree:
```
├── binder
│   └── environment.yml
├── data
│   ├── images
│   └── logs
├── notebooks
│   ├── analysis.ipynb
│   ├── interactive_graph.ipynb
│   ├── other_stats.ipynb
│   └── pubmed_api.ipynb
├── scripts
│   ├── create_forges_stat.py
│   ├── get_info_gh.py
│   ├── get_info_pm.py
│   ├── get_info_swh.py
│   ├── get_links.py
│   └── pbmd_tools.py
├── LICENSE
├── README.md
└── Snakefile
```
