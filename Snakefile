rule all:
    input:
        "forges_stat.png",
        "swh.png",
        "last_update.png"


rule create_forges_stat:
    input:
        script="scripts/create_forges_stat.py",
        envfile=".env",
    output:
        "PMIDs.txt",
        "stats_github.json",
        "stats_gitlab.json",
        "stats_sourceforge.json",
        "stats_googlecode.json",
        "stats_bitbucket.json"
    conda:
        "environment.yml"
    log:
        "forge_stats.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_info_pm:
    input:
        script="scripts/get_info_pm.py",
        ids="PMIDs.txt"
    output:
        "articles_pminfo.tsv"
    conda:
        "environment.yml"
    log:
        "pm_info.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_links:
    input:
        script="scripts/get_links.py",
        data="articles_pminfo.tsv"
    output:
        "articles_links.tsv"
    conda:
        "environment.yml"
    log:
        "links.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_info_gh:
    input:
        script="scripts/get_info_gh.py",
        data="articles_links.tsv"
    output:
        "articles_ghinfo.tsv"
    conda:
        "environment.yml"
    log:
        "gh_info.log"
    shell:
        "python {input.script} | tee {log}"
        
rule get_info_swh:
    input:
        script="scripts/get_info_swh.py",
        data="articles_ghinfo.tsv"
    output:
        "articles_swhinfo.tsv"
    conda:
        "environment.yml"
    log:
        "swh_info.log"
    shell:
        "python {input.script} | tee {log}"

rule make_figures:
    input:
        "articles_swhinfo.tsv",
        "stats_github.json",
        "stats_gitlab.json",
        "stats_sourceforge.json",
        "stats_googlecode.json",
        "stats_bitbucket.json",
        notebook="scripts/analysis.ipynb",
    output:
        "data_stat.txt",
        "forges_stat.png",
        "swh.png",
        "last_update.png",
        "developpement_stat.png",
        "developpement.png"
    conda:
        "environment.yml"
    log:
        "fig_info.log"
    shell:
        "jupyter nbconvert --to html --execute {input.notebook} | tee {log}"