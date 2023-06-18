import json
import os
import pandas as pd
from tqdm import tqdm

import pbmd_tools as pbmd


pbmd.read_tokens(".env")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PUBMED_TOKEN = os.environ.get("PUBMED_TOKEN")


db = "pubmed"
domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
retmode = "json"
queries_github = []
queries_gitlab = []
queries_sourceforge = []
queries_googlecode = []
queries_bitbucket = []

#creating queries for every forge and every year
for year in range(2009, 2023):
    queries_github.append(f'((github.com[Title/Abstract])) AND (("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication]))')
    queries_gitlab.append(f'((https://gitlab[Title/Abstract])) AND (("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication]))')
    queries_sourceforge.append(f'((sourceforge.net[Title/Abstract])) AND (("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication]))')
    queries_googlecode.append(f'(googlecode) AND ("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication])')
    queries_bitbucket.append(f'(bitbucket.org[Title/Abstract]) AND ("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication])')


#dictionaries for stocking the number of articles for each forge for each year
#example: {'2009': 0, '2010': 5, '2011': 15, ... }

PMIDs = []
PMIDs_all = []

stats_github = pbmd.get_forges_stat(queries_github, PMIDs)
stats_gitlab = pbmd.get_forges_stat(queries_gitlab, PMIDs_all)
stats_sourceforge = pbmd.get_forges_stat(queries_sourceforge, PMIDs_all)
stats_googlecode = pbmd.get_forges_stat(queries_googlecode, PMIDs_all)
stats_bitbucket = pbmd.get_forges_stat(queries_bitbucket, PMIDs_all)

print(f"\n{len(PMIDs)} articles with 'github.com' found in PubMed")

#checking that there is no duplicates
PMIDs = list(set(PMIDs))

#saving the statistics to reuse it in another notebook
#saving the statistics to reuse it in another notebook

with open("data/PMIDs.txt", "w") as f:
    for PMID in PMIDs:
        f.write(str(PMID)+"\n")
with open("data/stats_github.json", "w") as f:
    json.dump(stats_github, f)
with open("data/stats_gitlab.json", "w") as f:
    json.dump(stats_gitlab, f)
with open("data/stats_sourceforge.json", "w") as f:
    json.dump(stats_sourceforge, f)    
with open("data/stats_googlecode.json", "w") as f:
    json.dump(stats_googlecode, f)
with open("data/stats_bitbucket.json", "w") as f:
    json.dump(stats_bitbucket, f)

