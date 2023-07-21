from linkify_it import LinkifyIt
import pandas as pd
import re
import requests
from tqdm import tqdm
import xmltodict
import dotenv
import json
import os
import sys
import time
from datetime import datetime, timedelta


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


def record_api_error(query="", 
                     attempt=1, 
                     response=None, 
                     output_name="error.log"):
    """Record API error.

    Parameters
    ----------
    query : str
        Query URL to the API.
    attempt : int
        Attempt to query the API.
    response: requests.Response
        Response from the API.
    output_name: str
        File name to store error messages.
    """
    with open(output_name, "w") as error_file:
        error_file.write(f"Attempt: {attempt}\n")
        error_file.write(f"Query URL: {query}\n")
        error_file.write(f"Status code: {response.status_code}\n")
        error_file.write(f"Header: ")
        error_file.write(json.dumps(dict(response.headers), indent=4))

##############################################################################
####################################----PUBMED----############################
##############################################################################

def fill_empty_years(years, df):
    missing_years = [year for year in years if year not in set(df['year'])]
    missing_years_df = pd.DataFrame({'year': missing_years, 'count': 0})
    df = pd.concat([df, missing_years_df], ignore_index=True)
    df.sort_values('year', inplace=True)
    
    return df

def create_links_stat(files, 
                      file_path = "data/xml/", 
                      log = "results/tmp/log_files/log_create_links_stat(.txt"):
    links_stat = {}
    
    linkify = (
        LinkifyIt()
        .set({"fuzzy_email": False}) 
    )

    for file in files:
        with open(f"{file_path}{file}", "r") as f:
            try:
                summary = xmltodict.parse(f.read())
                abstract = get_abstract_from_summary(summary, log)
            except:
                abstract = None

            if abstract != None:

                if linkify.test(abstract):
                    for match in linkify.match(abstract):
                        link = match.raw
                        try:
                            key = link.split('/')[2]
                        except:
                            try:
                                key = link.split('/')[0]
                            except:
                                key = link
                        if key in links_stat:
                            links_stat[key] += 1
                        else:
                            links_stat[key] = 1
                
    return clean_links_dict(links_stat)
    


def clean_links_dict(links_stat):

    links_stat_lower = {}

    for key in links_stat.keys():
        if key.lower() in links_stat_lower:
            links_stat_lower[key.lower()] += links_stat[key]
        else:
            links_stat_lower[key.lower()] = links_stat[key]

    keys_to_modify = [key for key in links_stat_lower.keys() if key.startswith('www')]

    for key in keys_to_modify:
        if key[4:] in links_stat_lower:
            links_stat_lower[key[4:]] += links_stat_lower[key]
        else:
            links_stat_lower[key[4:]] = links_stat_lower[key]
        del links_stat_lower[key]
    
    sorted_links = {k: v for k, v in sorted(links_stat_lower.items(), key=lambda item: item[1], reverse=True)}
        
    return sorted_links


def query_pubmed(query, year_start, year_end, output_name):
    
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "json"
    token = os.environ.get("PUBMED_TOKEN")
    df = pd.DataFrame({'year': [], 'PMID': []})
    
    for year in range(year_start, year_end+1):
        query_year = (
            f'{query} AND "{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication]'
        )
        
        queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmax=9999&retmode={retmode}&term={query_year}&api_key={token}"
        response = requests.get(queryLinkSearch)
        if response.status_code != 200:
            print(f"Cannot get statistics for year {year}")
            print("Aborting...")
            break
            
        result = response.json()['esearchresult']
        nb_ids = int(result['count'])
        batch_nb = (nb_ids // 9999) + 1
        is_leap_year = int(year % 4 == 0)
        batch_size = (365 + is_leap_year) // batch_nb
        date_start = f"{year}/01/01"
        for batch in range(batch_nb):
            if batch == batch_nb-1 and batch_nb != 1:
                date_end = add_days(date_start, batch_size-is_leap_year)
            else:
                date_end = add_days(date_start, batch_size-1)
            query_batch = f'(({query} AND (("{date_start}"[Date - Publication] : "{date_end}"[Date - Publication]))'
            queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmax=9999&retmode={retmode}&term={query_batch}&api_key={token}"
            response = requests.get(queryLinkSearch)
            pubmed_json = response.json()
            ids = pubmed_json["esearchresult"]["idlist"]
            df_batch = pd.DataFrame({"year": [str(year)]*len(ids), "PMID": ids})
            
            df = pd.concat([df, df_batch], ignore_index=True)
            date_start = add_days(date_end, 1)

    df = df.drop_duplicates(subset=["PMID"], keep="first")
    df = df.reset_index(drop=True)
    df.to_csv(output_name, sep='\t', index=False)
    return df
    
    
def get_forges_stat(queries, PMIDs):
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "json"
    token = os.environ.get("PUBMED_TOKEN")
    stats = {}
    for query in tqdm(queries):
        nb = 0 #number of articles for this query
        queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmode={retmode}&retmax=9999&api_key={token}&term={query}"
        response = requests.get(queryLinkSearch)
        pubmed_json = response.json()
        if response.status_code != 200:
            record_api_error(
                query=queryLinkSearch,
                response=response
            )
            response.raise_for_status()
        for id in pubmed_json["esearchresult"]["idlist"]:
            #checking if there are any dublicates in PubMed IDs (it happens 
            #because of the PubDate that can be EPubDate or normal)
            if id not in PMIDs:
                nb += 1
                PMIDs.append(id)
        #query[-33:-29] - it is the year of this query
        stats[query[-33:-29]] = nb 
    return stats

  
def add_days(date_string, n):
    date_object = datetime.strptime(date_string, "%Y/%m/%d")
    new_date = date_object + timedelta(days=n)
    new_date_string = new_date.strftime("%Y/%m/%d")

    return new_date_string

def get_all_pmids(queries):
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "json"
    df = pd.DataFrame({'year': [], 'PMID': []})

    for query in tqdm(queries):
        queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmax=9999&retmode={retmode}&term={query}"
        response = requests.get(queryLinkSearch)
        if response.status_code == 200:
            result = response.json()['esearchresult']
            nb_ids = int(result['count'])
            if nb_ids > 9999:
                batch_nb = (nb_ids // 9999) + 2
                batch_size = 365 // batch_nb
                date_start = query[-68:-58]
                for batch in range(batch_nb):
                    date_end = add_days(date_start, batch_size)
                    query = f'(("http"[Title/Abstract]) OR ("https"[Title/Abstract])) AND (("{date_start}"[Date - Publication] : "{date_end}"[Date - Publication]))'
                    queryLinkSearch = f"{domain}/esearch.fcgi?db={db}&retmax=9999&retmode={retmode}&term={query}"
                    response = requests.get(queryLinkSearch)
                    pubmed_json = response.json()
                    for id in pubmed_json["esearchresult"]["idlist"]:
                        new_row = pd.DataFrame({'year': [query[-33:-29]], 'PMID': [id]})
                        df = pd.concat([df, new_row], ignore_index=True)
                    date_start = date_end
            else:
                response = requests.get(queryLinkSearch)
                pubmed_json = response.json()
                for id in pubmed_json["esearchresult"]["idlist"]:
                    new_row = pd.DataFrame({'year': [query[-33:-29]], 'PMID': [id]})
                    df = pd.concat([df, new_row], ignore_index=True)
                    
    df = df.drop_duplicates(subset=['PMID'])
    df = df.reset_index(drop=True)
    
    return df

  
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

def parse_xml(PMID, log_file):
    
    with open(f'data/xml/{PMID}.xml', 'r') as f:
        with open(log_file, "a") as f_log:
            f_log.write(f"\n{PMID} : ")
        summary = xmltodict.parse(f.read())

    abstract = get_abstract_from_summary(summary, log_file)
    pubdate = get_pubdate_from_summary(summary, log_file)
    title = get_title_from_summary(summary, log_file)
    journal = get_journal_from_summary(summary, log_file)
    doi = get_doi_from_summary(summary, log_file) 
    
    return PMID, pubdate, doi, journal, title, abstract


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



def download_pubmed_abstract(
        pmid=36540970,
        token="",
        xml_name="36540970.xml",
        log_name="36540970_error.log",
        attempt=1
    ):
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
    attempt : int
        Attempt to download data.

    Query example
    -------------
    https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=36540970&retmode=xml&rettype=abstract
    """
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "xml"
    wait_time = 0.10  # 10 requests / second = 1 request / 0.1 second
    if attempt > 1:
        wait_time = wait_time + 10 * (attempt - 1)
    query_url = f"{domain}/efetch.fcgi?db={db}&id={pmid}&retmode={retmode}&rettype=abstract&api_key={token}"
    response = requests.get(query_url)
    if response.status_code != 200:
        record_api_error(
            query=query_url,
            attempt=attempt,
            response=response,
            output_name=log_name
        )
        response.raise_for_status()
    with open(xml_name, "w") as xml_file:
        xml_file.write(response.text)
    # Wait to avoid rate limit
    time.sleep(wait_time)


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


def get_repo_info(pmid=0, url="", token="", log_name=""):
    """
    Get GitHub repository info.
    
    Example: https://api.github.com/repos/LMSE/FYRMENT
    
    Parameters
    ----------
    pmid : str
        PubMed PMID.
    url : str
        GitHub repo url.
    token : str
        Access token for github.
    log_name : str
        File name for logs.

    Returns
    -------
    info : list
        A list with the date of creation, the date of update and if the repository is a fork.
    """
    
    headers = {'Authorization': f"Token {token}"}
    owner = get_owner_from_link(url)
    repo = get_repo_from_link(url)
    query = f"https://api.github.com/repos/{owner}/{repo}"
    
    info = {"date_created": None, "date_updated": None, "fork": None}
    response = requests.get(query, headers=headers)
    if response.status_code == 200:
        repository_info = response.json()
        info["fork"] = repository_info["fork"]
        info["date_created"] = repository_info["created_at"].split("T")[0]
        info["date_updated"] = repository_info["updated_at"].split("T")[0]
    else:
        with open(log_name, "a") as log_file:
            log_file.write(f"Error with PMID: {pmid} URL: {url} Status code: {response.status_code} Answer: {response.json()}\n")
    return info


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