# Research of Current Trends in Bioinformatics Software Sharing and Archiving


Software plays a vital role in modern scientific research, making it imperative to uphold both the accessibility and high quality of scientific software. Recognizing the significance of sustainable and reproducible science, Software Heritage (https://www.softwareheritage.org/) serves as a global archive for software preservation. This project focuses on examining the current trends in the development of bioinformatic software by gathering information from the abstracts of articles published on PubMed (https://pubmed.ncbi.nlm.nih.gov/). By utilizing the APIs of PubMed, GitHub, and Software Heritage, we collect diverse information regarding approximately 10,000 scientific software packages. Subsequently, our analysis aims to determine the proportion of archived software, assess the developmental dynamics, and evaluate the accessibility of software through the provided publication links. Furthermore, the workflow is implemented using Snakemake, facilitating the seamless initiation of the analysis from scratch.

[![Python 3.10.9](https://img.shields.io/badge/python-%E2%89%A5_3.10.9-blue.svg)](https://www.python.org/downloads/release/python-397/)
[![Conda 22.11.1](https://img.shields.io/badge/conda-%E2%89%A5_22.11.1-green.svg)](https://docs.conda.io/en/latest/miniconda.html)
[![GitHub last commit](https://img.shields.io/github/last-commit/zhukovanadezhda/bioinformatics-software.svg)](https://github.com/zhukovanadezhda/bioinformatics-software)
![GitHub stars](https://img.shields.io/github/stars/zhukovanadezhda/bioinformatics-software.svg?style=social)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/zhukovanadezhda/bioinformatics-software/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/zhukovanadezhda/bioinformatics-software)

# Run the analysis

## Clone the repository

Clone the repository:

```bash
git clone https://github.com/zhukovanadezhda/bioinformatics-software.git
cd bioinformatics-software
```
## Setup your conda environment

Install [miniconda](https://docs.conda.io/en/latest/miniconda.html) and [mamba](https://github.com/mamba-org/mamba). Create the `bioinfosoft` conda environment:

```bash
mamba env create -f binder/environment.yml
conda activate bioinfosoft
```

To deactivate an active environment, use:

```
conda deactivate
```


## Launch the program

To launch the analysis with Snakemake workflow, use:

```bash
snakemake --cores 1 --use-conda
```

All the results will appear in the `data` folder.


# Dependency tree:
```
├── binder
│   └── environment.yml
├── data
│   ├── images
│   └── log_files
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
