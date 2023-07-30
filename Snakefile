import dotenv
import json
import os
import pathlib
import time

import pandas as pd
from tqdm import tqdm

from scripts import pbmd_tools as tools


# First things first: read PubMed and GitHub API tokens.
# The workflow cannot go further without them.
tools.read_tokens(".env")


def get_pubmed_xml(wildcards):
    """
    Get the list of xml files to download.
    
    It requires the file listing all PMIDs created in a previous rule.
    Use the 'checkpoint' instruction.
    """
    with checkpoints.query_pubmed_forges.get().output.http.open() as pmids_file:
        pmids_http = pd.read_csv("results/pubmed/articles_with_http.tsv", sep='\t')["PMID"].to_list()
        pmids_github = pd.read_csv("results/pubmed/articles_with_github.tsv", sep='\t')["PMID"].to_list()
        pmids = list(set(pmids_http + pmids_github))
        return expand("data/pubmed/{pmid}.xml", pmid=pmids)
        

rule all:
    input:
        get_pubmed_xml,
        "results/images/stat_http.png",
        "results/data_collection_summary.txt"


checkpoint query_pubmed_forges:
    """Blabla explain why do we use gitlab and not gitlab.com
    fot googlecode - explain
    """
    output:
        github="results/pubmed/articles_with_github.tsv",
        gitlab="results/pubmed/articles_with_gitlab.tsv",
        sourceforge="results/pubmed/articles_with_sourceforge.tsv",
        googlecode="results/pubmed/articles_with_googlecode.tsv",
        bitbucket="results/pubmed/articles_with_bitbucket.tsv",
        http="results/pubmed/articles_with_http.tsv"
    log:
        "results/pubmed/log_files/log_create_forges_stats.log"
    run:
        PUBMED_TOKEN = os.environ.get("PUBMED_TOKEN")
        queries = (
            ('"github.com"[tiab:~0]', output.github),
            ('"gitlab"[tiab]', output.gitlab),
            ('"sourceforge.net"[tiab:~0]', output.sourceforge),
            ('("googlecode.com"[tiab:~0] OR "code.google.com"[tiab:~0])', output.googlecode),
            ('"bitbucket.org"[tiab:~0]', output.bitbucket),
            ('("http"[tiab]) OR ("https"[tiab]))', output.http)
        )
        for query_str, query_output_name in queries:
            tools.query_pubmed(
                query=query_str,
                token=PUBMED_TOKEN,
                year_start=2009, year_end=2022, 
                output_name=query_output_name
            )
            
           
rule analyse_xml_http:
    input:
        get_pubmed_xml,
        http="results/pubmed/articles_with_http.tsv"
    output:
        "results/tmp/links_http_stat.json"
    run:
        pmids_http = pd.read_csv(input.http, sep="\t")["PMID"].to_list()
        files = [file for file in os.listdir("data/pubmed/") if file.endswith("xml") and int(file.split(".")[0]) in pmids_http]
        
        links_http_stat = tools.create_links_stat(files)

        with open(output[0], "w") as f:
            json.dump(links_http_stat, f)
        

rule make_forge_stat_figures:
    input:
        notebook="notebooks/analysis_forges.ipynb",
        github="results/pubmed/articles_with_github.tsv",
        gitlab="results/pubmed/articles_with_gitlab.tsv",
        sourceforge="results/pubmed/articles_with_sourceforge.tsv",
        googlecode="results/pubmed/articles_with_googlecode.tsv",
        bitbucket="results/pubmed/articles_with_bitbucket.tsv",
        http="results/pubmed/articles_with_http.tsv",
        links_stats ="results/pubmed/links_http_stat.json"
    output:
        "results/images/stat_forges.png",
        "results/images/stat_http.png"
    shell:
        "jupyter nbconvert --to html --execute {input.notebook}"      
        
        
rule extract_info_from_pubmed_xml:
    input:
        get_pubmed_xml,
        github="results/pubmed/articles_with_github.tsv",
    output:
        results="results/articles_info_pubmed.tsv"
    log:
        name="logs/extract_info_from_pubmed_xml.txt"
    run:
        # Remove old log file.
        pathlib.Path(log.name).unlink(missing_ok=True)
        # List all PMIDs to parse.
        PMIDs = pd.read_csv(input.github, sep="\t")["PMID"].to_list()
        df = pd.DataFrame(
            columns=["publication_date", "DOI", "journal", "title", "abstract",
            "GitHub_link_raw", "GitHub_link_clean", "GitHub_repo_owner", "GitHub_repo_name"])
        df.index.name = "PMID"
        for pmid in tqdm(PMIDs):
            # Parse the xml file.
            info = tools.parse_pubmed_xml(
                                pmid=pmid,
                                xml_name=f"data/pubmed/{pmid}.xml",
                                log_name=log.name
                                )
            # Handle GitHub link.
            info["GitHub_link_raw"] = tools.extract_link_from_abstract(info["abstract"])
            info["GitHub_link_clean"] = tools.clean_link(info["GitHub_link_raw"])
            info["GitHub_repo_owner"], info["GitHub_repo_name"] = tools.extract_github_repo_owner_name_from_link(info["GitHub_link_clean"])
            for column in df.columns:
                df.at[pmid, column] = info[column]
        df.to_csv(output.results, sep="\t", index=True)
        
        
rule get_info_github:
    input:
        data="results/articles_info_pubmed.tsv"
    output:
        results="results/articles_info_pubmed_github.tsv"
    log:
        name="logs/get_info_github.txt"
    run:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
        # Remove old log file.
        pathlib.Path(log.name).unlink(missing_ok=True)
        
        df = pd.read_csv(input.data, sep="\t", index_col="PMID")
        PMIDs = df[ df["GitHub_repo_name"].notna() ].index.to_list()
        for pmid in tqdm(PMIDs):    
            info = tools.get_repo_info(
                pmid=pmid,
                url=df.loc[pmid, "GitHub_link_clean"],
                token=GITHUB_TOKEN,
                log_name=log.name
            )
            df.loc[pmid, "date_repo_created"] = info["date_created"]
            df.loc[pmid, "date_repo_updated"] = info["date_updated"]
            df.loc[pmid, "is_fork"] = info["fork"]
        df.to_csv(output.results, sep="\t", index=True)
        
        
rule get_info_software_heritage:
    input:
        data="results/articles_info_pubmed_github.tsv"
    output:
        results="results/articles_info_pubmed_github_software_heritage.tsv"
    run:
        df = pd.read_csv(input.data, sep="\t", index_col="PMID")
        for pmid in tqdm(df.index):
            info = {"is_archived": False, "date_archived": None}
            if df.loc[pmid, "GitHub_repo_name"]:
                info = tools.check_repository_is_archived_in_swh(
                    df.at[pmid, "GitHub_link_clean"]
                )
            df.at[pmid, "is_archived"] = info["is_archived"]
            df.at[pmid, "date_archived"] = info["date_archived"]
        df.to_csv(outputs.result, sep="\t", index=True)
    

rule make_figures:
    input:
        data="results/articles_info_pubmed_github_software_heritage.tsv",
        notebook="notebooks/analysis.ipynb"
    output:
        "results/data_collection_summary.txt",
        "results/images/stat_dev.png",
        report("results/images/stat_dynam.png"),
        report("results/images/stat_forges.png"),
        report("results/images/stat_hist.png"),
        report("results/images/stat_last_updt.png"),
        report("results/images/stat_swh.png")
    shell:
        "jupyter nbconvert --to html --execute {input.notebook}"


rule download_pubmed_xml:
    output:
        xml_name="data/pubmed/{pmid}.xml"
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