import json
import os
import pandas as pd
import dotenv
import xmltodict
import time
from tqdm import tqdm

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
        pmids_http = pd.read_csv("results/tmp/http.tsv", sep='\t')["PMID"].to_list()
        pmids_github = pd.read_csv("results/tmp/github.tsv", sep='\t')["PMID"].to_list()
        pmids = list(set(pmids_http + pmids_github))
        return expand("data/xml/{pmid}.xml", pmid=pmids)
        

rule all:
    input:
        get_xml,
        "results/images/stat_http.png",
        "results/tmp/articles_info_pubmed_github.tsv"


checkpoint create_forges_stats:
    """Blabla explain why do we use gitlab and not gitlab.com
    fot googlecode - explain
    """
    output:
        github_stats="results/tmp/github.tsv",
        gitlab_stats="results/tmp/gitlab.tsv",
        sourceforge_stats="results/tmp/sourceforge.tsv",
        googlecode_stats="results/tmp/googlecode.tsv",
        bitbucket_stats="results/tmp/bitbucket.tsv",
        http_stats="results/tmp/http.tsv"
    log:
        "results/tmp/log_files/log_create_forges_stats.log"
    run:
        PUBMED_TOKEN = os.environ.get("PUBMED_TOKEN")
        queries = (
            ('"github.com"[tiab:~0]', "results/tmp/github.tsv"),
            ('"gitlab"[tiab]', "results/tmp/gitlab.tsv"),
            ('"sourceforge.net"[tiab:~0]', "results/tmp/sourceforge.tsv"),
            ('("googlecode.com"[tiab:~0] OR "code.google.com"[tiab:~0])', 
            "results/tmp/googlecode.tsv"),
            ('"bitbucket.org"[tiab:~0]', "results/tmp/bitbucket.tsv"),
            ('("http"[tiab]) OR ("https"[tiab]))', "results/tmp/http.tsv"),
        )
        for query_str, query_output in queries:
            tools.query_pubmed(
                query=query_str,
                year_start=2009, year_end=2022, 
                output_name=query_output
            )
            
           
rule analyse_xml_http:
    input:
        get_xml
    output:
        "results/tmp/links_http_stat.json"
    run:
        pmids_http = pd.read_csv("results/tmp/http.tsv", sep="\t")["PMID"].to_list()
        files = [file for file in os.listdir("data/xml/") if file.endswith("xml") and int(file.split(".")[0]) in pmids_http]
        
        links_http_stat = tools.create_links_stat(files)

        with open("results/tmp/links_http_stat.json", "w") as f:
            json.dump(links_http_stat, f)
        

rule make_forge_stat_figures:
    input:
        notebook="notebooks/analysis_forges.ipynb",
        github_stats="results/tmp/github.tsv",
        gitlab_stats="results/tmp/gitlab.tsv",
        sourceforge_stats="results/tmp/sourceforge.tsv",
        googlecode_stats="results/tmp/googlecode.tsv",
        bitbucket_stats="results/tmp/bitbucket.tsv",
        http_stats="results/tmp/http.tsv",
        links_stats ="results/tmp/links_http_stat.json"
    output:
        "results/images/stat_forges.png",
        "results/images/stat_http.png"
    shell:
        "jupyter nbconvert --to html --execute {input.notebook}"      
        
        
rule get_info_pubmed:
    input:
        data="results/tmp/github.tsv",
        get_xml
    output:
        result="results/tmp/articles_info_pubmed.tsv"
    run:
        PMIDs = pd.read_csv(input.data, sep="\t")["PMID"].to_list()

        results = []
        for PMID in PMIDs:
            results.append(tools.parse_xml(PMID, "results/tmp/log_files/log_get_info_pubmed.txt"))
            
        df = pd.DataFrame.from_records(results)
        df = df.rename(columns = {0: "PMID", 1: "PubDate", 2: "DOI", 3: "Journal", 4: "Title", 5: "Abstract"})
        df = df.drop_duplicates(subset = "PMID")
        df = df.reset_index(drop = True)
        
        df["GitHub_link_raw"] = df["Abstract"].astype(str).apply(tools.get_link_from_abstract)
        df["GitHub_link_clean"] = df["GitHub_link_raw"].astype(str).apply(tools.clean_link)
        df["GitHub_owner"] = df["GitHub_link_clean"].apply(tools.get_owner_from_link)
        df["GitHub_repo"] = df["GitHub_link_clean"].apply(tools.get_repo_from_link)
        
        df.to_csv(output.result, sep="\t", index=False)
        
        
rule get_info_github:
    input:
        data="results/tmp/articles_info_pubmed.tsv"
    output:
        "results/tmp/articles_info_pubmed_github.tsv"
    run:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

        df = pd.read_csv(input.data, sep="\t")
        PMIDs = df["PMID"][df["GitHub_repo"].notna()].to_list()

        for PMID in tqdm(PMIDs):

            with open("results/tmp/log_files/log_get_info_github.txt", "a") as f:
                f.write(f"\n\n PMID: {PMID}, GitHub link: {df[df['PMID'] == PMID]['GitHub_link_clean'].values[0]}")

            info = tools.get_repo_info(df[df['PMID']==PMID]['GitHub_owner'].values[0], 
                                      df[df['PMID']==PMID]['GitHub_repo'].values[0], 
                                      GITHUB_TOKEN, "results/tmp/log_files/log_get_info_github.txt")
            idx = df.index[df['PMID'] == PMID][0]
            df.loc[idx, "Repo_created_at"] = tools.get_repo_date_created(info)
            df.loc[idx, "Repo_updated_at"] = tools.get_repo_date_updated(info)
            df.loc[idx, "Fork"] = tools.is_fork(info)
            
            time.sleep(1) 

        df.to_csv(output.result, sep="\t", index=False)
        
        
rule get_info_software_heritage:
    input:
        data="results/tmp/articles_info_pubmed_github.tsv"
    output:
        result="results/articles_info_pubmed_github_software_heritage.tsv"
    run:
        df = pd.read_csv(input.data, sep="\t")
        PMIDs = df['PMID'][df['GitHub_owner'].notna()].to_list()

        for PMID in tqdm(PMIDs):

            try:
                info = tools.check_is_in_softwh(df[df['PMID']==PMID]["GitHub_link_clean"].values[0])
            except:
                try:
                    info = tools.check_is_in_softwh(df[df['PMID']==PMID]["GitHub_link_clean"].values[0])
                except:
                    continue

            idx = df.index[df['PMID'] == PMID][0]

            df.loc[idx, "In_SoftWH"] = tools.is_in_softwh(info)
            df.loc[idx, "Archived"] = tools.get_date_archived(info)

        df.to_csv(output.result, sep='\t', index=False)
    

rule make_figures:
    input:
        data="results/articles_info_pubmed_github_software_heritage.tsv",
        notebook="notebooks/analysis.ipynb"
    output:
        "results/data_stat.txt",
        "results/images/stat_dev.png",
        report("results/images/stat_dynam.png"),
        report("results/images/stat_forges.png"),
        report("results/images/stat_hist.png"),
        report("results/images/stat_last_updt.png"),
        report("results/images/stat_swh.png")
    shell:
        "jupyter nbconvert --to html --execute {input.notebook}"


"""
# I don't know what was this used for ?

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
"""

onsuccess:
    print("WORKFLOW COMPLETED SUCCESSFULLY!")