import re
import requests
import xmltodict
import dotenv
import os
import sys

db = 'pubmed'
domain = 'https://www.ncbi.nlm.nih.gov/entrez/eutils'
nresults = 15_000
retmode = 'xml'

def read_tokens():
    """Read tokens from .env file.
    
    Returns
    -------
    pub, git : str
        Tokens.
        
    """
    dotenv.load_dotenv(".env")
    if "GITHUB_KEY" not in os.environ:
        sys.exit("Cannot find Github token")
    if "PUBMED_KEY" not in os.environ:
        sys.exit("Cannot find PubMed token")


def get_summary(PMID, token):
    """Obtaining information about an article published in PubMed using the PubMed API.

    Parameters
    ----------
    PMID : str
        The PubMed id of the article.
    log_error_sum: list
        The list to stock the errors provided by this code.

    Returns
    -------
    dic : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
        
    Example of query
    -------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36540970&retmode=xml&rettype=abstract
    
    """
    queryLinkSearch = f'{domain}/efetch.fcgi?db={db}&id={PMID}&retmax={nresults}&retmode={retmode}&rettype=abstract&api_key={token}'  
    response = requests.get(queryLinkSearch)
    dic = xmltodict.parse(response.content)
    return dic

def get_abstract_from_summary(summary):
    """Obtaining abstract from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    abstract : str
        The article abctact.
    error : str
        A list to stock the errors provided by this function.
    """
    error = []
    
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        abstract_raw = article['MedlineCitation']['Article']['Abstract']['AbstractText']
        if isinstance(abstract_raw, list):
            abstract = ""
            for d in abstract_raw:
                abstract += d['#text'] + " "    
        elif isinstance(abstract_raw, dict):
            abstract = ""
            abstract += abstract_raw['#text'] + " "
        else:
            abstract = article['MedlineCitation']['Article']['Abstract']['AbstractText']  
    except:
        error.append(f"{PMID} : no abstract found")
        
    return abstract, error
    
def get_pubdate_from_summary(summary):
    """Obtaining pubdate from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    pubdate : str
        The article abctact.
    error : str
        A list to stock the errors provided by this function.
    """
    error = []
    
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        date = article['MedlineCitation']['DateCompleted']
        pubdate = date['Year'] + '-' + date['Month'] + '-' + date['Day']
    except:
        try:
            article = res['PubmedArticleSet']['PubmedArticle']
            date = article['MedlineCitation']['Article']['ArticleDate']
            pubdate = date['Year'] + '-' + date['Month'] + '-' + date['Day']
        except:
            error.append(f"{PMID} : no publication date found")
        
    return pubdate, error

def get_title_from_summary(summary):
    """Obtaining title from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    title : str
        The article abctact.
    error : str
        A list to stock the errors provided by this function.
    """
    error = []
    
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        Tit = article['MedlineCitation']['Article']['ArticleTitle']
        if isinstance(Tit, dict) or type(Tit) == "<class 'dict'>":
            for d in Tit.keys():
                title += Tit[d] + ' '
        else:
            title = Tit
    except:
        error.append(f"{PMID} : no title found")
        
    return title, error


def get_journal_from_summary(summary):
    """Obtaining journal name from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    journal : str
        The article abctact.
    error : str
        A list to stock the errors provided by this function.
    """
    error = []
    
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        journal = article['MedlineCitation']['Article']['Journal']['Title']
    except:
        error.append(f"{PMID} : no journal found")
    
    return journal, error

def get_doi_from_summary(summary):
    """Obtaining doi from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    doi : str
        The article abctact.
    error : str
        A list to stock the errors provided by this function.
    """
    error = []
    
    try:
        try:
            article = res['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['PubmedData']['ArticleIdList']['ArticleId']
        except:
            article = res['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['MedlineCitation']['Article']['ELocationID']
        if isinstance(ELocationID_list, dict) or type(ELocationID_list) == "<class 'dict'>":
            if "doi" in ELocationID_list.values():
                doi = ELocationID_list["#text"]
        else:
            for dictionary in ELocationID_list:
                if "doi" in dictionary.values():
                    doi = dictionary["#text"]
    except:
        error.append(f"{PMID} : no DOI found")
    
    return journal, error
    

def get_info(PMID, token):
    """Obtaining information about an article published in PubMed using the PubMed API.

    Parameters
    ----------
    dic : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_error_sum: list
        The list to stock the errors provided by this code.

    Returns
    -------
    Abstract : str
        The article abctact.
    PubDate : str
        The date of the article publication in the YYYY-MM-DD format.
    DOI : str
        The DOI of the article.
    Journal : str
        The journal name.
    Title : str
        The article title.
    log_error_sum : list
        The list with all the cases when the function have not managed to obtain one of the value listed above.
    """
    info = {"abstract":"", "title":"", "journal":"", "publication_date":"", "doi":"", }
    error = []
    res = get_summary(PMID, token)
    
    # Abstract
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        abstract_raw = article['MedlineCitation']['Article']['Abstract']['AbstractText']
        if isinstance(abstract_raw, list):
            Abstract = ''
            for d in abstract_raw:
                info["abstract"] += d['#text'] + ' '    
        elif isinstance(abstract_raw, dict):
            info["abstract"] = ""
            info["abstract"] += abstract_raw['#text'] + ' '
        else:
            info["abstract"] = article['MedlineCitation']['Article']['Abstract']['AbstractText']  
    except:
        error.append(f"{PMID} : no abstract found")
        
    # PubDate
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        date = article['MedlineCitation']['DateCompleted']
        info["publication_date"] = date['Year'] + '-' + date['Month'] + '-' + date['Day']
    except:
        try:
            article = res['PubmedArticleSet']['PubmedArticle']
            date = article['MedlineCitation']['Article']['ArticleDate']
            info["publication_date"] = date['Year'] + '-' + date['Month'] + '-' + date['Day']
        except:
            error.append(f"{PMID} : no publication date found")
        
    # Title and Journal 
    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        Tit = article['MedlineCitation']['Article']['ArticleTitle']
        if isinstance(Tit, dict) or type(Tit) == "<class 'dict'>":
            for d in Tit.keys():
                info["title"] += Tit[d] + ' '
        else:
            info["title"] = Tit
    except:
        error.append(f"{PMID} : no title found")

    try:
        article = res['PubmedArticleSet']['PubmedArticle']
        info["journal"] = article['MedlineCitation']['Article']['Journal']['Title']
    except:
        error.append(f"{PMID} : no journal found")
        
    # DOI
    DOI = None
    try:
        try:
            article = res['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['PubmedData']['ArticleIdList']['ArticleId']
        except:
            article = res['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['MedlineCitation']['Article']['ELocationID']
        if isinstance(ELocationID_list, dict) or type(ELocationID_list) == "<class 'dict'>":
            if "doi" in ELocationID_list.values():
                info["doi"] = ELocationID_list["#text"]
        else:
            for dictionary in ELocationID_list:
                #print(1)
                if "doi" in dictionary.values():
                    #print(2)
                    info["doi"] = dictionary["#text"]
    except:
        error.append(f"{PMID} : no DOI found")
        
    return info, error


def get_link(text):
    
    regex = ["github.com[^\n ,):;'+}>]*"]
    links_with_point = ''
    
    for rgx in regex:
        if (links_with_point == '') and re.search(rgx, text, re.IGNORECASE):
                links_with_point = re.findall(rgx, text, re.IGNORECASE)
    links = ''
    for link in links_with_point :
        links += link + ' '
        
    return links

def clean_link(links):
    links_fin = ''
    for link in links.split(' '):
        if link != "":
            if not link.startswith("https://"):
                link = "https://" + link
            if link[-2] == ")":
                link = link[:-2]
            if link[-1] == "." or link[-1] == ']' or link[-1] == '"':
                link = link[:-1]
            if link[-4:] == '.git':
                link = link[:-4]
            if link[-1] != "/":
                links_fin += link + "/" + ' '
            else:
                links_fin += link + ' '
                
    return links_fin


def get_repo_info(link, access_token):
    """
    Get GitHub repository info.
    
    Example: http://
    """
    owner = str(link).split('/')[3]
    repo = str(link).split('/')[4]
    
    headers = {'Authorization': f"Token {access_token}"}
    url = f"https://api.github.com/repos/{owner}/{repo}"
    
    info = {"date_created": None, "date_updated": None, "errors": None}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repository_info = response.json()
        info["date_created"] = repository_info["created_at"].split("T")[0]
        info["date_updated"] = updated_at = repository_info["updated_at"].split("T")[0]
    else:
        info["errors"] = f"Error with URL: {url} Status code: {response.status_code} Answer: {response.json()}"
    return info