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


df = pd.read_csv('articles_links.tsv', sep='\t')
PMIDs = df['PMID'][df['GitHub_repo'].notna()].to_list()

for PMID in tqdm(PMIDs):

    with open("gitstat.txt", "a") as f:
        f.write(f"\n\n PMID: {PMID}, GitHub link: {df[df['PMID'] == PMID]['GitHub_link_clean'].values[0]}")

    info = pbmd.get_repo_info(df[df['PMID']==PMID]['GitHub_owner'].values[0], df[df['PMID']==PMID]['GitHub_repo'].values[0], GITHUB_TOKEN, "gitstat.txt")

    if info["status"]: 
        idx = df.index[df['PMID'] == PMID][0]

        df.loc[idx, "Repo_created_at"] = pbmd.get_repo_date_created(info)
        df.loc[idx, "Repo_updated_at"] = pbmd.get_repo_date_updated(info)
        df.loc[idx, "Fork"] = pbmd.is_fork(info)
    else:
        
        time.sleep(3600)
        
        info = pbmd.get_repo_info(df[df['PMID']==PMID]['GitHub_owner'].values[0], df[df['PMID']==PMID]['GitHub_repo'].values[0], GITHUB_TOKEN, "gitstat.txt")
        idx = df.index[df['PMID'] == PMID][0]
        df.loc[idx, "Repo_created_at"] = pbmd.get_repo_date_created(info)
        df.loc[idx, "Repo_updated_at"] = pbmd.get_repo_date_updated(info)
        df.loc[idx, "Fork"] = pbmd.is_fork(info)
        
df.to_csv('articles_ghinfo.tsv', sep='\t', index=False)

