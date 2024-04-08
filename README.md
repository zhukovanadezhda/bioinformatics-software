# Research of Current Trends in Bioinformatics Software Sharing and Archiving


Software plays a vital role in modern scientific research, making it imperative to uphold both the accessibility and high quality of scientific software. Recognizing the significance of sustainable and reproducible science, Software Heritage (https://www.softwareheritage.org/) serves as a global archive for software preservation. This project focuses on examining the current trends in the development of bioinformatic software by gathering information from the abstracts of articles published on PubMed (https://pubmed.ncbi.nlm.nih.gov/). By utilizing the APIs of PubMed, GitHub, and Software Heritage, we collect diverse information regarding approximately 10,000 scientific software packages. Subsequently, our analysis aims to determine the proportion of archived software, assess the developmental dynamics, and evaluate the accessibility of software through the provided publication links. Furthermore, the workflow is implemented using Snakemake, facilitating the seamless initiation of the analysis from scratch.

[![GitHub last commit](https://img.shields.io/github/last-commit/zhukovanadezhda/bioinformatics-software.svg)](https://github.com/zhukovanadezhda/bioinformatics-software)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/zhukovanadezhda/bioinformatics-software/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/zhukovanadezhda/bioinformatics-software)

## Create the environment

### Clone the repository

Clone the repository:

```bash
git clone https://github.com/zhukovanadezhda/bioinformatics-software.git
cd bioinformatics-software
```
### Setup the conda environment

Install [miniconda](https://docs.conda.io/en/latest/miniconda.html) and [mamba](https://github.com/mamba-org/mamba). Create the `bioinfosoft` conda environment:

```bash
mamba env create -f binder/environment.yml
```

### Load the environment

```bash
conda activate bioinfosoft
```

Remark: to deactivate an active environment, use:

```bash
conda deactivate
```


## Get API keys

The workflow analysis requires API keys for PubMed, GitHub and Software Heritage.

To get API keys:

- For PubMed, go at the bottom of the [NCBI Account Settings](https://account.ncbi.nlm.nih.gov/settings/) page.
- For GitHub, go on the [Personnal access tokens](https://github.com/settings/tokens) page of your account. There is not need to select specific scopes.

Create the file `.env` to store API keys in the following format:

```
GITHUB_TOKEN=...
PUBMED_TOKEN=...
SWH_TOKEN=...
```


## Run the analysis

Run the analysis with the Snakemake workflow:

```bash
snakemake --cores 1 --use-conda
```

All the results will be stored in the `data` folder.
