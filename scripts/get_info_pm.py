import time
import os
import pandas as pd
from tqdm import tqdm

import pbmd_tools as pbmd

pbmd.read_tokens()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PUBMED_TOKEN = os.environ.get("PUBMED_TOKEN")


PMIDs = []

with open("data/PMIDs.txt", "r") as f:
    for line in f.readlines():
        PMIDs.append(line.strip())
        
results = []

#API Pubmed rate limit is 10 request per second with a token and 3 request par second without it

#count = 0
for PMID in tqdm(PMIDs):
    #count += 1
    #if count % 10 == 0:
    #    time.sleep(1)
    
    try:
        summary = pbmd.get_summary(PMID, PUBMED_TOKEN, "data/log_files/status.txt")
    except:
        try:
            summary = pbmd.get_summary(PMID, PUBMED_TOKEN, "data/log_files/status.txt")
        except:
            continue
            
    abstract = pbmd.get_abstract_from_summary(summary, "data/log_files/status.txt")
    pubdate = pbmd.get_pubdate_from_summary(summary, "data/log_files/status.txt")
    title = pbmd.get_title_from_summary(summary, "data/log_files/status.txt")
    journal = pbmd.get_journal_from_summary(summary, "data/log_files/status.txt")
    doi = pbmd.get_doi_from_summary(summary, "data/log_files/status.txt")  

    results.append((PMID, pubdate, doi, journal, title, abstract))

df = pd.DataFrame.from_records(results)
df = df.rename(columns = {0: 'PMID', 1: 'PubDate', 2: 'DOI', 3: 'Journal', 4: 'Title', 5 : 'Abstract'})
df = df.drop_duplicates(subset = 'PMID')
df = df.reset_index(drop = True)

df.to_csv('data/articles_pminfo.tsv', sep = '\t', index = False)
