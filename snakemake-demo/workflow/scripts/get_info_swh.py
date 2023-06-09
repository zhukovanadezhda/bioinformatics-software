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

df = pd.read_csv('articles_ghinfo.tsv', sep='\t')
PMIDs = df['PMID'][df['GitHub_owner'].notna()].to_list()

for PMID in tqdm(PMIDs):
    
    try:
        info = pbmd.check_is_in_softwh(df[df['PMID']==PMID]['GitHub_link_clean'].values[0])
    except:
        try:
            info = pbmd.check_is_in_softwh(df[df['PMID']==PMID]['GitHub_link_clean'].values[0])
        except:
            continue

    idx = df.index[df['PMID'] == PMID][0]

    df.loc[idx, "In_SoftWH"] = pbmd.is_in_softwh(info)
    df.loc[idx, "Archived"] = pbmd.get_date_archived(info)
    
df.to_csv('articles_swhinfo.tsv', sep='\t', index=False)