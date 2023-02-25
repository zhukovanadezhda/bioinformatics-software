import re
import requests
import xmltodict
import dotenv
import os

db = 'pubmed'
domain = 'https://www.ncbi.nlm.nih.gov/entrez/eutils'
nresults = 15000
retmode = 'xml'

def read_tokens():
    """Read tokens from .env file.
    Returns
    -------
    tuple
        Tokens.
    """
    dotenv.load_dotenv(".env")
    if "GITHUB_KEY" in os.environ:
        print("Found GitHub token.")
        git = os.environ.get("GITHUB_KEY")
    else:
        print("Token is missing.")
    if "PUBMED_KEY" in os.environ:
        print("Found PubMed token.")
        pub = os.environ.get("PUBMED_KEY")
    else:
        print("Token is missing.")
    return pub, git

def get_summary(PMID, log_error_sum):
    """Obtaining information about an article published in PubMed using the PubMed API.

    Parameters
    ----------
    PMID : str
        The PubMed id of the article.
    log_error_sum: list
        The list to stock the errors provided by this code.

    Returns
    -------
    PubDate : str
        The date of the article publication in the YYYY-MM-DD format.
    DOI : str
        The DOI of the article.
    Journal : str
        The journal name.
    Title : str
        The article title.
    Abstract : str
        The article abctact.
    log_error_sum : list
        The list with all the cases when the function have not managed to obtain one of the value listed above.
        
    """
    
    API_KEY = read_tokens()[0]
    
    queryLinkSearch = f'{domain}/efetch.fcgi?db={db}&id={PMID}&retmax={nresults}&retmode={retmode}&rettype=abstract&api_key={API_KEY}'
    response = requests.get(queryLinkSearch)
    dic = xmltodict.parse(response.content)
    # Abstract
    try:
        abstract_raw = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Abstract']['AbstractText']
        if not isinstance(abstract_raw, list):
            Abstract = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Abstract']['AbstractText']
        else:
            Abstract = ''
            for d in abstract_raw:
                Abstract += d['#text']
    except:
        Abstract = None
        log_error_sum.append('No Abstract found :' + str(PMID) + '\n')
    # PubDate
    try:
        try:
            PubDate = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['ArticleDate']['Year'] + '-' + dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['ArticleDate']['Month'] + '-' + dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['ArticleDate']['Day']
        except:
            log_error_sum.append('No Noramal Article Date found :' + str(PMID) + '\n')
            try:
                PubDate = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']['Year'] + '-' + dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']['Month']
            except:
                PubDate = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']['Year']
    except:
        PubDate = None
        log_error_sum.append('No Article Date found at all :' + str(PMID) + '\n')
    # Title and Journal 
    try:
        Title = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['ArticleTitle']
    except:
        Title = None
        log_error_sum.append('No Title found :' + str(PMID) + '\n')
    try:
        Journal = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['Journal']['Title']
    except:
        Journal = None
        log_error_sum.append('No Journal Name found :' + str(PMID) + '\n')
    # DOI
    DOI = None
    try:
        try:
            ELocationID_list = dic['PubmedArticleSet']['PubmedArticle']['PubmedData']['ArticleIdList']['ArticleId']
        except:
            ELocationID_list = dic['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['Article']['ELocationID']
        if isinstance(ELocationID_list, dict) or type(ELocationID_list) == "<class 'dict'>":
            if "doi" in ELocationID_list.values():
                DOI = ELocationID_list["#text"]
        else:
            for dictionary in ELocationID_list:
                #print(1)
                if "doi" in dictionary.values():
                    #print(2)
                    DOI = dictionary["#text"]
    except:
        DOI = None
        log_error_sum.append('No DOI found :' + str(PMID) + '\n')
        
    return PubDate, DOI, Journal, Title, Abstract, log_error_sum

def get_link(df, PMID):
    
    regex = ["github.com[^\n ,)]*"]
    links_with_point = ''
    
    for rgx in regex:
        if (links_with_point == '') and re.search(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
                links_with_point = re.findall(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
    links = []
    for link in links_with_point :
        
        links.append(link) 
        
    return links

def clean_link(df, PMID):
    regex = ["github.com[^\n ,)]*"]
    links_with_point = ''
    
    for rgx in regex:
        if (links_with_point == '') and re.search(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
                links_with_point = re.findall(rgx, str(df.loc[df["PMID"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
    links = []
    for link in links_with_point :
        links.append(link)
    links_fin = []
    for link in links:
        if link != "":
            if not link.startswith("https://"):
                link = "https://" + link
            if link[-2] == ")":
                link = link[:-2]
            if link[-1] == ")" or link[-1] == "." or link[-1] == "," or link[-1] == ":":
                link = link[:-1]
            if link[-1] != "/":
                links_fin.append(link+"/")
            else:
                links_fin.append(link)
    return links_fin

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

def get_repo_info(link, log_error):
    
    owner = str(link).split('/')[3]
    access_token = read_tokens()[1]
    headers = {'Authorization':"Token "+access_token}
    repo = str(link).split('/')[4]
    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = requests.get(url,headers=headers)
    if response.status_code == 200:
        repository_info = response.json()
        created_at = repository_info["created_at"]
        updated_at = repository_info["updated_at"]
    else:
        log_error.append(f"Error with URL: {url} Status code: {response.status_code}\n")
        return None, None
    return created_at.split('T')[0], updated_at.split('T')[0], log_error