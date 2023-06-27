import re
import requests
from tqdm import tqdm
import xmltodict
import dotenv
import json
import os
import sys
import time

############################################################################################
#################################----TECHNICAL----##########################################
############################################################################################

def read_tokens(path):
    """Read tokens from .env file.   
    """
    dotenv.load_dotenv(path)
    if "GITHUB_TOKEN" not in os.environ:
        sys.exit("Cannot find Github token")
    if "PUBMED_TOKEN" not in os.environ:
        sys.exit("Cannot find PubMed token")


############################################################################################
####################################----PUBMED----##########################################
############################################################################################

def get_forges_stat(queries, PMIDs):
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "json"
    stats = {}
    for query in tqdm(queries):
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
        stats[query[-33:-29]] = nb 
    return stats

def is_software(PMID, access_token, log_file):
    tags = []
    dict = pbmd.get_summary(PMID, access_token, log_file)['PubmedArticleSet']['PubmedArticle']['MedlineCitation']['MeshHeadingList']['MeshHeading']
    try:
        tags.append(dict['DescriptorName']['#text'])
    except:
        for i in dict:
            tags.append(i['DescriptorName']['#text'])
    if 'Software' in tags:
        return 1
    else:
        return 0


def get_summary(PMID, access_token, log_file):
    """Obtaining information about an article published in PubMed using the PubMed API.

    Parameters
    ----------
    PMID : int
        The PubMed id of the article.
    access_token : str
        Access token for github.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
        
    Example of query
    -------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36540970&retmode=xml&rettype=abstract
    
    """
    db = 'pubmed'
    domain = 'https://www.ncbi.nlm.nih.gov/entrez/eutils'
    retmode = 'xml'
    queryLinkSearch = f'{domain}/efetch.fcgi?db={db}&id={PMID}&retmode={retmode}&rettype=abstract&api_key={access_token}'  
    response = requests.get(queryLinkSearch)
    summary = xmltodict.parse(response.content)
    
    with open(log_file, "a") as f:
        f.write(f"\n{PMID} : ")
    
    return summary
        

def download_pubmed_abstract(pmid, token, xml_name, log_name):
    """Download abstract from Pubmed in XML format.

    The E-utilities/NCBI API has a rate limit of 10 requests per second
    for user with an API key.
    See: https://www.ncbi.nlm.nih.gov/books/NBK25497/
    Do get an API key, visit https://www.ncbi.nlm.nih.gov/account/

    Parameters
    ----------
    pmid : int
        The PubMed id of the article.
    token : str
        Pubmed API token.
    xml_name : str
        XML file name to store the abstract.
    log_name : str
        File name to store error messages.

    Query example
    -------------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36540970&retmode=xml&rettype=abstract
    """
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "xml"
    sleep_time = 0.10  # 10 requests / second = 1 request / 0.1 second
    query = f"{domain}/efetch.fcgi?db={db}&id={pmid}&retmode={retmode}&rettype=abstract&api_key={token}"
    response = requests.get(query)
    if response.status_code != 200:
        with open(log_name, "w") as error_file:
            error_file.write(f"{response.status_code}")
            error_file.write(json.dumps(response.headers, indent=4))
        response.raise_for_status()
    with open(xml_name, "w") as xml_file:
        print(response.status_code)
        print(response.headers)
        xml_file.write(response.text)
    # Wait to avoid rate limit
    time.sleep(sleep_time)


def get_abstract_from_summary(summary,  log_file):
    """Obtaining abstract from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    abstract : str
        The article abctact.
        
    """
    try:
        try:
            article = summary['PubmedArticleSet']['PubmedArticle']
            abstract_raw = article['MedlineCitation']['Article']['Abstract']['AbstractText']
        except:
            article = summary['PubmedArticleSet']['PubmedBookArticle']['BookDocument']
            abstract_raw = article['Abstract']['AbstractText']
        if isinstance(abstract_raw, str):
            abstract = abstract_raw
        elif isinstance(abstract_raw, list):
            abstract = ""
            for d in abstract_raw:
                try:
                    abstract += d['#text'] + " " 
                except:
                    continue
        else:
            try: 
                abstract = ""
                abstract += abstract_raw['#text'] + " "
            except:
                for d in abstract_raw:
                    try:
                        abstract += abstract_raw[d] + " " 
                    except:
                        continue

        return abstract
    except:
        with open(log_file, "a") as f:
            f.write(f"no abstract found, ")
        return None

def get_pubdate_from_summary(summary, log_file):
    """Obtaining pubdate from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    pubdate : str
        Pubdate.

    Example of (weird) query
    -------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36579134&retmode=xml&rettype=abstract
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36930770&retmode=xml&rettype=abstract
 
    """
    try:
        article = summary['PubmedArticleSet']['PubmedArticle']
        date = article['MedlineCitation']['Article']['ArticleDate']
        pubdate = date['Year'] + '-' + date['Month'] + '-' + date['Day']

        return convert_date(pubdate)
    except:
        try:
            article = summary['PubmedArticleSet']['PubmedArticle']
            date = article['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']
            pubdate = date['Year'] + '-' + date['Month'] + '-' + date['Day']
                
            return convert_date(pubdate)
        except:  
            with open(log_file, "a") as f:
                f.write(f"no publication date found, ")
            return None
             

def convert_date(date_str):
    """Converting date to a standart format.

    Parameters
    ----------
    date_str : str
        Date in YYYY-MM-DD format (example: 2023-Jan-01 or 2022-5-17)

    Returns
    -------
    converted_date : str
        Date in a standart YYYY-MM-DD format (example: 2023-01-01 or 2022-05-17).
 
    """
    months = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06', 
              'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
              '1': '01', '2': '02', '3': '03', '4': '04', '5': '05', '6': '06', 
              '7': '07', '8': '08', '9': '09', '10': '10', '11': '11', '12': '12'}
    parts = date_str.split('-')
    year = parts[0]
    month = months.get(parts[1], parts[1])
    day = parts[2]
    converted_date = f"{year}-{month}-{day}"
        
    return converted_date


def get_title_from_summary(summary,  log_file):
    """Obtaining title from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    title : str
        The article abctact.
    
    Example of a (weird) query
    -------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=32983048&retmode=xml&rettype=abstract
 
    """
    
    try:
        article = summary['PubmedArticleSet']['PubmedArticle']
        title_raw = article['MedlineCitation']['Article']['ArticleTitle']
        if isinstance(title_raw, list):
            title = ""
            for d in title_raw:
                title += d['#text'] + " "    
        elif isinstance(title_raw, dict):
            title = ""
            for i in title_raw.keys():
                if isinstance(title_raw[i], list):
                    for j in title_raw[i]:
                        title += j + " "
                else:
                    title += title_raw[i] + " "
        else:
            title = title_raw

        return title  
    except:
        with open(log_file, "a") as f:
            f.write(f"no title found, ")
        return None
        

def get_journal_from_summary(summary,  log_file):
    """Obtaining journal name from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    journal : str
        The article abctact.
        
    """ 
    try:
        article = summary['PubmedArticleSet']['PubmedArticle']
        journal = article['MedlineCitation']['Article']['Journal']['Title']
        return journal
    except:
        with open(log_file, "a") as f:
            f.write(f"no jouranl found, ")
        return None


def get_doi_from_summary(summary,  log_file):
    """Obtaining doi from the dictionary with summary returned by PubMed API.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.
    log_file : str
        A file to store information about the errors provided by this function.

    Returns
    -------
    doi : str
        The article abctact.
        
    Example of (weird) query
    -------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36579134&retmode=xml&rettype=abstract
  
    """  
    try:
        try:
            article = summary['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['PubmedData']['ArticleIdList']['ArticleId']
            
        except:
            article = summary['PubmedArticleSet']['PubmedArticle']
            ELocationID_list = article['MedlineCitation']['Article']['ELocationID']
            
        if isinstance(ELocationID_list, dict) or type(ELocationID_list) == "<class 'dict'>":
            if "doi" in ELocationID_list.values():
                doi = ELocationID_list["#text"]
        else:
            for dictionary in ELocationID_list:
                if "doi" in dictionary.values():
                    doi = dictionary["#text"]
        return doi
    except:
        with open(log_file, "a") as f:
            f.write(f"no doi found \n")
        return None            


def get_link_from_abstract(text):
    """
    Get a Github link from an abstract.
    
    Parameters
    ----------
    text : str
        An abstract with a link.

    Returns
    -------
    link_with_point : str
        Link to a github repository extracted from an abstract.
    """
    if text == None:
        return None
    
    rgx = "github.com[^\n ,):;'+}>•]*"
       
    if len(re.findall(rgx, text, re.IGNORECASE)) > 1:
        link_with_point  = re.findall(rgx, text, re.IGNORECASE)[0]
    else:
        link_with_point  = str(re.findall(rgx, text, re.IGNORECASE))[2:-2]

    return link_with_point       

def get_gitlab_link(text):

    if text == None:
        return None
    
    rgx = "[^\n /,\):;'\+}>•]*gitlab\.[^\n ,\):;'\+}>•]*"
       
    if len(re.findall(rgx, text, re.IGNORECASE)) > 1:
        link_with_point  = re.findall(rgx, text, re.IGNORECASE)[0]
    else:
        link_with_point  = str(re.findall(rgx, text, re.IGNORECASE))[2:-2]

    return link_with_point   

def is_gitlabcom(link):
    
    if "gitlab.com" in link:
        return 1
    else:
        return 0


def clean_link(link):
    """
    Get a proper Github link.
    
    Parameters
    ----------
    link : str
        Link to a github repository extracted from an abstract.

    Returns
    -------
    link : str
        Link to a github repository ready to use.
    """
    
    if link != "":
        if link.count('.') > 1:
            link = re.sub(r"\.[a-z][^.]*$", "", link)    
        if link[-5:] == 'https':
            link = link[:-5]
        if link[-13:] == 'Supplementary':
            link = link[:-13]
        if link[-12:] == 'Communicated':
            link = link[:-12]
        if link[-7:] == 'Contact':
            link = link[:-7]
        #if link[-8:] == 'Database':
        #    link = link[:-8]
        if not link.startswith("https://"):
            link = "https://" + link
        if '//' in link[8:]:
            link = link[:8] + link[8:].replace('//', '/')
        if "\\" in link:
            link = link.replace("\\", '')      
        if "\\\\" in link:
            link = link.replace("\\\\", '')          
        if link[-2] == ")" or link[-2] == "/" or link[-2] == "]" or link[-2] == '"':
            link = link[:-2]
        if link[-1] == "." or link[-1] == ']' or link[-1] == '"' or link[-1] == "/":
            link = link[:-1]
        if link[-1] == "." or link[-1] == ']' or link[-1] == '"' or link[-1] == "/":
            link = link[:-1]
        if link[-4:] == '.git':
            link = link[:-4]
        if link[-1] != "/":
            link += "/" 
                
    return link 

############################################################################################
####################################----GITHUB----##########################################
############################################################################################

def get_last_commit_files(owner, repo, access_token):
    headers = {'Authorization': f"Token {access_token}"}   
    url = f'https://api.github.com/repos/{owner}/{repo}/commits'
    response = requests.get(url, headers=headers)
    data = response.json()
    if response.status_code == 200:
        if len(data) > 0:
            last_commit_sha = data[0]['sha']
            files_url = f'{url}/{last_commit_sha}'
            files_response = requests.get(files_url, headers=headers)
            files_data = files_response.json()
            if files_response.status_code == 200:
                files_changed = [file['filename'] for file in files_data['files']]
                return files_changed, files_response.status_code 
            else:
                return None, files_response.status_code
    return None, response.status_code

def get_owner_from_link(link):
    """
    Get Github repository owner name and the name of the repository.
    
    Parameters
    ----------
    link : str
        Link to a github repository.

    Returns
    -------
    owner : str
        Owner name.
    """
    if link != "":
        owner = str(link).split('/')[3]
        return owner.strip()
    else:
        return None

    
def get_repo_from_link(link):
    """
    Get Github repository owner name and the name of the repository.
    
    Parameters
    ----------
    link : str
        Link to a github repository.

    Returns
    -------
    repo : str
        Repository name.
    """
    if link != "" and len(str(link).split('/')) > 5:
        repo = str(link).split('/')[4]
        return repo.strip()
    else:
        return None


def get_repo_info(owner, repo, access_token,  log_file):
    """
    Get GitHub repository info.
    
    Example: https://api.github.com/repos/LMSE/FYRMENT
    
    Parameters
    ----------
    owner : str
        Owner name.
    repo : str
        Repository name.
    access_token : str
        Access token for github.

    Returns
    -------
    info : list
        A list with the date of creation, the date of update and if the repository is a fork.
    """
    
    headers = {'Authorization': f"Token {access_token}"}
    url = f"https://api.github.com/repos/{owner}/{repo}"
    
    info = {"date_created": None, "date_updated": None, "fork": 0, "status": None}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        info["status"] = True
        repository_info = response.json()
        if repository_info["fork"]:
            info["fork"] = 1 
        info["date_created"] = repository_info["created_at"].split("T")[0]
        info["date_updated"] = repository_info["updated_at"].split("T")[0]
    else:
        if response.status_code == 403:
            info["status"] = False
        else:
            info["status"] = True
        with open(log_file, "a") as f:
            f.write(f"Error with URL: {url} Status code: {response.status_code} Answer: {response.json()}\n")
    return info

    
def get_repo_date_created(info):
    """
    Get the date of creation of the GitHub repository.
    
    Parameters
    ----------
    info : list
        A list with the date of creation, the date of update and if the repository is a fork.

    Returns
    -------
    date_created : str
        A date of creation of the repository
    """
    return info["date_created"]
    
def get_repo_date_updated(info):
    """
    Get the date of the last update of the GitHub repository.
    
    Parameters
    ----------
    info : list
        A list with the date of creation, the date of update and if the repository is a fork.

    Returns
    -------
    date_updated : str
        A date of last update of the repository
    """
    return info["date_updated"]

def is_fork(info):
    """
    Get 1 if the GitHub repository is a fork and 0 otherwise.
    
    Parameters
    ----------
    info : list
        A list with the date of creation, the date of update and if the repository is a fork.

    Returns
    -------
    fork : int
        1 if the GitHub repository is a fork and 0 otherwise
    """
    return info["fork"]

############################################################################################
####################################----SOFTWH----##########################################
############################################################################################

def check_is_in_softwh(url):
    """
    Get Software Heritage repository info.
    
    Example: https://archive.softwareheritage.org/api/1/origin/https://github.com/jupyterlite/jupyterlite/visit/latest/
    
    Parameters
    ----------
    url : str
        Repository GitHub link.

    Returns
    -------
    info : list
        A list with if the repositary is archived in SWH and if so the date of archiving.
    """
    info = {"is_in": None, "date_archived": None}
    queryLinkSearch = f'https://archive.softwareheritage.org/api/1/origin/{url}visit/latest/'  
    response = requests.get(queryLinkSearch)
    if 'exception' not in response.json():
        info["is_in"] = 1
        info["date_archived"] = response.json()['date'].split('T')[0]
    else:
        info["is_in"] = 0
    return info


def is_in_softwh(info):
    """
    Get 1 if the GitHub repository is in SWH and 0 otherwise.
    
    Parameters
    ----------
    info : list
        A list with if the repositary is archived in SWH and if so the date of archiving.

    Returns
    -------
    is_in : int
        1 if the GitHub repository is in SWH and 0 otherwise
    """
    return info["is_in"]


def get_date_archived(info):
    """
    Get the date of archiving of the GitHub repository.
    
    Parameters
    ----------
    info : list
        A list with if the repositary is archived in SWH and if so the date of archiving.

    Returns
    -------
    date_archived : str
        The date of archiving of the GitHub repository
    """
    return info["date_archived"]