import re
import requests

db = 'pubmed'
domain = 'https://www.ncbi.nlm.nih.gov/entrez/eutils'
nresults = 100
query = '"github.com"[Title/Abstract] NOT "github.com"[Title]'
retmode = 'json'

def get_abstract(PMID):
    queryLinkSearch = f'{domain}/efetch.fcgi?db={db}&id={PMID}&retmax={nresults}&retmode={retmode}&rettype=abstract'
    response = requests.get(queryLinkSearch)
    return response.text

def get_link(df, PMID):
    
    regex = ["github.com[^\n .,)]*"]
    links_with_point = ''
    
    for rgx in regex:
        if (links_with_point == '') and re.search(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
                links_with_point = re.findall(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
    links = []
    for link in links_with_point :
        links.append(link) 
        
    return links

def clean_link(link_array):
    links = []
    for link in link_array:
        if link != "":
            if not link.startswith("https://"):
                link = "https://" + link
            if link[-2] == ")":
                link = link[:-2]
            if link[-1] == ")" or link[-1] == "." or link[-1] == "," or link[-1] == ",":
                link = link[:-1]
        links.append(link+'/')
        
    return links

def get_phrase_with_link(df, PMID):
    
    regex = ["\.[^.]*[./]github[^ ]* [^.]*[^ ]*\.", "\.[^.]*[./]github[^ ]*", "[^.]*github[^ ]*", "[a-zA-Z0-9 .,/:\'\"!?]{101}github[^ ]*[a-zA-Z0-9 .,/:\'\"!?()]{100}"]
    phrase_with_point = ''
    
    for rgx in regex:
        if (phrase_with_point == "") and re.search(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
            phrase_with_point = re.findall(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
    phrases = []
    for phrase in phrase_with_point :
        phrase = phrase[2:]
        phrases.append(phrase)
        
    return ' '.join(phrases)

def get_repo_info(link):
    
    owner = str(link).split('/')[3]
    access_token='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' 
    headers = {'Authorization':"Token "+access_token}
    repo = str(link).split('/')[4]
    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = requests.get(url,headers=headers)
    if response.status_code == 200:
        repository_info = response.json()
        created_at = repository_info["created_at"]
        updated_at = repository_info["updated_at"]
    else:
        print(f"Error with URL: {url}")
        print(f"Status code: {response.status_code}")
        #print(response.headers)
        return None, None
    return created_at.split('T')[0], updated_at.split('T')[0]