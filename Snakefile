import os
import pandas as pd
import dotenv
import xmltodict
import time
from scripts import pbmd_tools as tools


# First things first: read PubMed and GitHub API tokens.
# The workflow cannot go further without them.
tools.read_tokens(".env")


def get_xml(wildcards):
    """
    Get the list of xml files to download.
    
    It requires the file listing all PMIDs created in a previous rule.
    Use the 'checkpoint' instruction.
    """
    with checkpoints.create_forges_stats.get().output.http_stats.open() as pmids_file:
        pmids_http = pd.read_csv("data/http.tsv", sep='\t')['PMID'].to_list()
        pmids_github = pd.read_csv("data/github.tsv", sep='\t')['PMID'].to_list()
        pmids = list(set(pmids_http + pmids_github))
        return expand("data/xml/{pmid}.xml", pmid=pmids)
        

rule all:
    input:
        get_xml


checkpoint create_forges_stats:
    """Blabla explain why do we use gitlab and not gitlab.com
    fot googlecode - explain
    """
    output:
        github_stats="data/github.tsv",
        gitlab_stats="data/gitlab.tsv",
        sourceforge_stats="data/sourceforge.tsv",
        googlecode_stats="data/googlecode.tsv",
        bitbucket_stats="data/bitbucket.tsv",
        http_stats="data/http.tsv"
    log:
        "data/log_files/forge_stats.log"
    run:
        PUBMED_TOKEN = os.environ.get("PUBMED_TOKEN")
        queries = (
            ('"github.com"[tiab:~0]', "data/github.tsv"),
            ('"gitlab"[tiab]', "data/gitlab.tsv"),
            ('"sourceforge.net"[tiab:~0]', "data/sourceforge.tsv"),
            ('("googlecode.com"[tiab:~0] OR "code.google.com"[tiab:~0])', 
            "data/googlecode.tsv"),
            ('"bitbucket.org"[tiab:~0]', "data/bitbucket.tsv"),
            ('("http"[tiab]) OR ("https"[tiab]))', "data/http.tsv"),
        )
        for query_str, query_output in queries:
            tools.query_pubmed(
                query=query_str,
                year_start=2009, year_end=2022, 
                output_name=query_output
            )
           
rule analyse_xml:
    input:
        get_xml
    output:
        "../data/links_http_stat.json"
        

rule make_forge_stat_figures:
    input:
        notebook="analysis_forges.ipynb",
        github_stats="data/github.tsv",
        gitlab_stats="data/gitlab.tsv",
        sourceforge_stats="data/sourceforge.tsv",
        googlecode_stats="data/googlecode.tsv",
        bitbucket_stats="data/bitbucket.tsv",
        http_stats="data/http.tsv"
    output:
        "results/images/stat_forges.png"
        "results/images/stat_http.png"
    shell:
        "jupyter nbconvert --execute {input.notebook}"                      
        
rule get_info_pubmed:
    input:
        "data/github.tsv",
        get_xml
    output:
        "data/articles_info_pubmed.tsv"
    run:
        PMIDs = pd.read_csv("data/github.tsv", sep='\t')['PMID'].to_list()
        results = []
        count = 0
        for PMID in PMIDs:
            count += 1
            if count % 10 == 0:
                time.sleep(1)

            results.append(tools.parse_xml(PMID, "data/log_files/status.txt"))
            
        df = pd.DataFrame.from_records(results)
        df = df.rename(columns = {0: 'PMID', 1: 'PubDate', 2: 'DOI', 3: 'Journal', 4: 'Title', 5: 'Abstract'})
        df = df.drop_duplicates(subset = 'PMID')
        df = df.reset_index(drop = True)
        
        df['GitHub_link_raw'] = df['Abstract'].astype(str).apply(tools.get_link_from_abstract)
        df['GitHub_link_clean'] = df['GitHub_link_raw'].astype(str).apply(tools.clean_link)
        df['GitHub_owner'] = df['GitHub_link_clean'].apply(tools.get_owner_from_link)
        df['GitHub_repo'] = df['GitHub_link_clean'].apply(tools.get_repo_from_link)
        
        df.to_csv('data/articles_info_pubmed.tsv', sep='\t', index=False)
        
        
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
        "data/images/stat_dev.png",
        report("data/images/stat_dynam.png"),
        report("data/images/stat_forges.png"),
        report("data/images/stat_hist.png"),
        report("data/images/stat_last_updt.png"),
        report("data/images/stat_swh.png")
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