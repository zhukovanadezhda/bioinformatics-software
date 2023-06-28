import os

import pandas as pd

from scripts import pbmd_tools as tools


# First thing first: read PubMed and GitHub API tokens.
# The workflow cannot go further without them.
tools.read_tokens(".env")


def get_xml(wildcards):
    """
    Get the list of xml files to download.
    
    It requires the file listing all PMIDs created in a previsous rule.
    Use the 'checkpoint' instruction.
    """
    with checkpoints.create_forges_stats.get().output.pmids.open() as pmids_file:
        pmids = pd.read_csv("data/PMIDs.txt", header=None)[0].tolist()
        return expand("data/xml/{pmid}.xml", pmid=pmids)
        

rule all_xml:
    input:
        get_xml


rule all:
    input:
        "data/images/forges_stat.png",
        "data/images/swh.png",
        "data/images/last_update.png"


checkpoint create_forges_stats:
    input:
        script="scripts/create_forges_stat.py",
        envfile=".env",
    output:
        pmids="data/PMIDs.txt",
        github_stats="data/stats_github.json",
        gitlab_stats="data/stats_gitlab.json",
        sourceforge_stats="data/stats_sourceforge.json",
        googlecode_stats="data/stats_googlecode.json",
        bitbucket_stats="data/stats_bitbucket.json"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/forge_stats.log"
    shell:
        "python {input.script} | tee {log}"


rule get_info_pm:
    input:
        script="scripts/get_info_pm.py",
        ids="data/PMIDs.txt"
    output:
        "data/articles_pminfo.tsv"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/pm_info.log"
    shell:
        "python {input.script} | tee {log}"

rule get_links:
    input:
        script="scripts/get_links.py",
        data="data/articles_pminfo.tsv"
    output:
        "data/articles_links.tsv"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/links.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_info_gh:
    input:
        script="scripts/get_info_gh.py",
        data="data/articles_links.tsv"
    output:
        "data/articles_ghinfo.tsv"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/gh_info.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_info_swh:
    input:
        script="scripts/get_info_swh.py",
        data="data/articles_ghinfo.tsv"
    output:
        "data/articles_swhinfo.tsv"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/.log"
    shell:
        "python {input.script} | tee {log}"

rule make_figures:
    input:
        "data/articles_swhinfo.tsv",
        "data/stats_github.json",
        "data/stats_gitlab.json",
        "data/stats_sourceforge.json",
        "data/stats_googlecode.json",
        "data/stats_bitbucket.json",
        notebook="notebooks/analysis.ipynb",
    output:
        "data/data_stat.txt",
        "data/images/forges_stat.png",
        "data/images/swh.png",
        "data/images/last_update.png",
        "data/images/developpement_stat.png",
        "data/images/developpement.png"
    conda:
        "binder/environment.yml"
    log:
        "data/log_files/fig_info.log"
    shell:
        "jupyter nbconvert --to html --execute {input.notebook} | tee {log}"


rule download_pubmed_abstract:
    output:
        xml_name="data/xml/{pmid}.xml"
    retries: 3
    resources:
        attempt=lambda wildcards, attempt: attempt
    run:
        print(resources.attempt)
        tools.download_pubmed_abstract(
            pmid=wildcards.pmid,
            token=os.getenv("PUBMED_TOKEN", ""),
            xml_name=output.xml_name,
            log_name=f"logs/{wildcards.pmid}_error_{resources.attempt}.log",
            attempt=resources.attempt
            )

onsuccess:
    print("WORKFLOW COMPLETED SUCCESSFULLY!")