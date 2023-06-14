from datetime import datetime
import json
import re
import time

import dotenv
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from tqdm import tqdm
import requests
import warnings
import xmltodict

import pbmd_tools as pbmd


pbmd.read_tokens()
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

stats_github = {}
stats_gitlab = {}
stats_sourceforge = {}
stats_googlecode = {}
stats_bitbucket = {}
PMIDs = []
PMIDs_all = []

for query in tqdm(queries_github):
    nb = 0 #number of articles for this query
    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=15000&term={query}"
    response = requests.get(queryLinkSearch)
    pubmed_json = response.json()
    for id in pubmed_json["esearchresult"]["idlist"]:
        #checking if there are any dublicates in PubMed IDs (it happens because of the PubDate that can be EPubDate or normal)
        if id not in PMIDs:
            nb += 1
            PMIDs.append(id)
    #query[38:42] - it is the year of this query
    stats_github[query[38:42]] = nb 
    
for query in tqdm(queries_bitbucket):
    nb = 0
    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=15000&term={query}"
    response = requests.get(queryLinkSearch)
    pubmed_json = response.json()
    for id in pubmed_json["esearchresult"]["idlist"]:
        if id not in PMIDs_all:
            nb += 1
            PMIDs_all.append(id)
    stats_bitbucket[query[38:42]] = nb
    
for query in tqdm(queries_gitlab):
    nb = 0
    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=15000&term={query}"
    response = requests.get(queryLinkSearch)
    pubmed_json = response.json()
    for id in pubmed_json["esearchresult"]["idlist"]:
        if id not in PMIDs_all:
            nb += 1
            PMIDs_all.append(id)
    stats_gitlab[query[42:46]] = nb
    
for query in tqdm(queries_sourceforge):
    nb = 0
    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=15000&term={query}"
    response = requests.get(queryLinkSearch)
    pubmed_json = response.json()
    for id in pubmed_json["esearchresult"]["idlist"]:
        if id not in PMIDs_all:
            nb += 1
            PMIDs_all.append(id)
    stats_sourceforge[query[43:47]] = nb
    
for query in tqdm(queries_googlecode):
    nb = 0
    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=15000&term={query}"
    response = requests.get(queryLinkSearch)
    pubmed_json = response.json()
    for id in pubmed_json["esearchresult"]["idlist"]:
        if id not in PMIDs_all:
            nb += 1
            PMIDs_all.append(id)
    stats_googlecode[query[19:23]] = nb

#checking that there is no duplicates
PMIDs = list(set(PMIDs))

#saving the statistics to reuse it in another notebook
with open("PMIDs.txt", "w") as f:
    for PMID in PMIDs:
        f.write(str(PMID)+"\n")
with open("stats_github.json", "w") as f:
    json.dump(stats_github, f)
with open("stats_gitlab.json", "w") as f:
    json.dump(stats_gitlab, f)
with open("stats_sourceforge.json", "w") as f:
    json.dump(stats_sourceforge, f)    
with open("stats_googlecode.json", "w") as f:
    json.dump(stats_googlecode, f)
with open("stats_bitbucket.json", "w") as f:
    json.dump(stats_bitbucket, f)

