import pandas as pd

import pbmd_tools as pbmd

df = pd.read_csv('data/articles_pminfo.tsv', sep='\t')

df['GitHub_link_raw'] = df['Abstract'].astype(str).apply(pbmd.get_link_from_abstract)
df['GitHub_link_clean'] = df['GitHub_link_raw'].astype(str).apply(pbmd.clean_link)
df['GitHub_owner'] = df['GitHub_link_clean'].apply(pbmd.get_owner_from_link)
df['GitHub_repo'] = df['GitHub_link_clean'].apply(pbmd.get_repo_from_link)

df.to_csv('data/articles_links.tsv', sep='\t', index=False)