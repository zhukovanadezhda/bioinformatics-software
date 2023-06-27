import os

from scripts import pbmd_tools as tools

tools.read_tokens(".env")


rule toto:
    input:
        expand("data/xml/{pmid}.xml", pmid=range(452366, 452399))

rule all:
    input:
        "data/images/forges_stat.png",
        "data/images/swh.png",
        "data/images/last_update.png"


rule create_forges_stat:
    input:
        script="scripts/create_forges_stat.py",
        envfile=".env",
    output:
        "data/PMIDs.txt",
        "data/stats_github.json",
        "data/stats_gitlab.json",
        "data/stats_sourceforge.json",
        "data/stats_googlecode.json",
        "data/stats_bitbucket.json"
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
        xml_name="data/xml/{pmid}.xml",
    run:
        tools.download_pubmed_abstract(
            wildcards.pmid,
            os.getenv("PUBMED_TOKEN", ""),
            output.xml_name,
            f"logs/{wildcards.pmid}_error.log"
            )

onsuccess:
    print("WORKFLOW COMPLETED SUCCESSFULLY!")