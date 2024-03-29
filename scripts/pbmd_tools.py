from datetime import datetime, timedelta
import json
import os
import sys
import time
import re

import dotenv
from linkify_it import LinkifyIt
from lxml import etree
import pandas as pd
import requests
from tqdm import tqdm
import xmltodict


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
                     output_name="error.log",
                     append_log=False):
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
    log_mode = "w"
    if append_log:
        log_mode = "a"
    with open(output_name, log_mode) as error_file:
        error_file.write(f"Attempt: {attempt}\n")
        error_file.write(f"Query URL: {query}\n")
        error_file.write(f"Status code: {response.status_code}\n")
        error_file.write("Header: ")
        error_file.write(f"{json.dumps(dict(response.headers), indent=4)}\n")
        error_file.write("Answer: ")
        error_file.write(f"{json.dumps(dict(response.json()), indent=4)}\n\n")


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


def query_pubmed(query="github[tiab]",
                 token="",
                 year_start=2018,
                 year_end=2022,
                 output_name="test.tsv"):
    db = "pubmed"
    domain = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "json"
    df = pd.DataFrame({"year": [], "PMID": []})
    
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
    print(f"Saved {output_name}")
    
 
def add_days(date_string, n):
    date_object = datetime.strptime(date_string, "%Y/%m/%d")
    new_date = date_object + timedelta(days=n)
    new_date_string = new_date.strftime("%Y/%m/%d")

    return new_date_string


def parse_pubmed_xml(pmid="", xml_name="", log_name="parse_pubmed_xml.log"):
    info = {"PMID": pmid, "publication_date": "", "DOI": "",
            "journal": "", "title": "", "abstract": ""}
    with open(xml_name, "r") as xml_file, open(log_name, "a") as log_file:
        xml_content = xml_file.read()
        error_message = ""
        try:
            xml_content_dict = xmltodict.parse(xml_content)
        except xmltodict.expat.ExpatError:
            return info
        # Extracting information from the xml file.
        info["abstract"] = extract_abstract_from_summary(xml_content)
        if not info["abstract"]:
            error_message += "no abstract found, "
        info["publication_date"] = extract_pubdate_from_summary(xml_content_dict)
        if not info["publication_date"]:
            error_message += "no publication date found, "
        info["title"] = extract_title_from_summary(xml_content_dict)
        if not info["title"]:
            error_message += "no title found, "
        info["journal"] = extract_journal_from_summary(xml_content_dict)
        if not info["journal"]:
            error_message += "no journal found, "
        info["DOI"] = extract_doi_from_summary(xml_content_dict)
        if not info["DOI"]:
            error_message += "no doi found"
        if error_message:
            log_file.write(f"{pmid}: {error_message}\n")
    return info


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
    base_url = "https://www.ncbi.nlm.nih.gov/entrez/eutils"
    retmode = "xml"
    wait_time = 0.10  # 10 requests / second = 1 request / 0.1 second
    if attempt > 1:
        wait_time = wait_time + 10 * (attempt - 1)
    query_url = (
        f"{base_url}/efetch.fcgi?db={db}&id={pmid}"
        f"&retmode={retmode}&rettype=abstract&api_key={token}"
    )
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


def extract_abstract_from_summary(content):
    """Extract article abstract from XML content.

    Parameters
    ----------
    content : str
        Content from the XML file provided by the PubMed API.

    Returns
    -------
    str
        The article abstract.
    """
    abstract = ""
    tree = etree.fromstring(content)
    # Abstracts are contained in AbstractText tags,
    # AbstractText tags can have nested tags for formatting.
    # Hence, .itertext() returns the text of the element
    # and its subelements.
    for element in tree.findall('.//AbstractText'):
        for text in element.itertext():
            abstract += text + " "
    return abstract


def extract_pubdate_from_summary(summary):
    """Extract article publication date from XML content.

    Some articles do not have a complete publication date,
    year and month are ususaly provided but day is missing.
    Examples:
    - https://pubmed.ncbi.nlm.nih.gov/25553811/
    - https://pubmed.ncbi.nlm.nih.gov/31871433/

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    str
        Publication date.
    """
    try:
        article = summary["PubmedArticleSet"]["PubmedArticle"]
        date = article["MedlineCitation"]["Article"]["ArticleDate"]
        pubdate = f"{date['Year']}-{date['Month']}-{date['Day']}"
    except KeyError:
        pass
    else:
        return normalize_date(pubdate)
    try:
        article = summary["PubmedArticleSet"]["PubmedArticle"]
        date = article["MedlineCitation"]["Article"]["Journal"]["JournalIssue"]["PubDate"]
        pubdate = f"{date['Year']}-{date['Month']}-{date['Day']}"
    except KeyError:
        pass
    else:
        return normalize_date(pubdate)
    # No ArticleDate neither PubDate
    # Example:
    # https://pubmed.ncbi.nlm.nih.gov/25344330/
    # https://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=25344330&retmode=xml&rettype=abstract
    try:
        article = summary["PubmedArticleSet"]["PubmedArticle"]
        date = article["MedlineCitation"]["DateCompleted"]
        pubdate = f"{date['Year']}-{date['Month']}-{date['Day']}"
    except KeyError:
        pass
    else:
        return normalize_date(pubdate)
    return ""


def normalize_date(date):
    """Normalize date to ISO-8601 standard format.

    Parameters
    ----------
    date_str : str
        Date in YYYY-XX-DD format (example: 2023-Jan-01 or 2022-5-17)

    Returns
    -------
    converted_date : str
        Date in a standard YYYY-MM-DD format (example: 2023-01-01 or 2022-05-17).
 
    """
    months = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06', 
              'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
              '1': '01', '2': '02', '3': '03', '4': '04', '5': '05', '6': '06', 
              '7': '07', '8': '08', '9': '09', '10': '10', '11': '11', '12': '12'}
    year, month, day = date.split('-')
    month = months.get(month, month)
    date_new = f"{year}-{month}-{day}"
    return date_new


def extract_title_from_summary(summary):
    """Extract article title from XML content.

    Title with weird characters cannot be extracted.
    For example: https://pubmed.ncbi.nlm.nih.gov/35846129/

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    str
        The article title.
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
        return ""
        

def extract_journal_from_summary(summary):
    """Extract article journal name from XML content.

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    str
        The article journal.
    """ 
    try:
        article = summary['PubmedArticleSet']['PubmedArticle']
        journal = article['MedlineCitation']['Article']['Journal']['Title']
        return journal
    except:
        return ""


def extract_doi_from_summary(summary):
    """Extract article DOI from XML content.

    Some articles do not have a DOI.
    Examples:
    - https://pubmed.ncbi.nlm.nih.gov/26262258/
    - https://pubmed.ncbi.nlm.nih.gov/32508484/

    Parameters
    ----------
    summary : dictionary
        A dictionary obtained from xml format provided by pubmed api entrez.

    Returns
    -------
    str
        The article DOI.  
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
        return ""  


def extract_link_from_abstract(text):
    """
    Extract a Github link from an article abstract.
    
    Parameters
    ----------
    text : str
        An article abstract.

    Returns
    -------
    str
        GitHub.com link.
    """
    if not text:
        return ""
    regex = "github.com[^\n ,):;'+}>•]*"
    hits = re.findall(regex, text, re.IGNORECASE)
    if not hits:
        return ""
    # If multiple GitHub links are found, return the first link only.
    return hits[0]


def get_gitlab_link(text):

    if not text:
        return ""
    
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
    str
        Link to a github repository ready to use.
    """
    if not link:
        return link
    # Remove everything after the last dot in the link.
    if link.count('.') > 1:
        link = re.sub(r"\.[a-z][^.]*$", "", link)
    # Remove words that could stick at the end of urls.
    # Sometimes 2 urls are sticked together.
    for word in ["https", "Supplementary", "Communicated", "Contact"]:
        if link.endswith(word):
            link = link[:-len(word)]
    if not link.startswith("https://"):
        link = "https://" + link
    if '//' in link[8:]:
        link = link[:8] + link[8:].replace('//', '/')
    if "\\" in link:
        link = link.replace("\\", "")
    if "\\\\" in link:
        link = link.replace("\\\\", "")
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
    headers = {"Authorization": f"Token {access_token}"}   
    query = f"https://api.github.com/repos/{owner}/{repo}/commits"
    response = requests.get(query, headers=headers)
    data = response.json()
    if response.status_code == 200:
        if len(data) > 0:
            last_commit_sha = data[0]['sha']
            files_url = f'{query}/{last_commit_sha}'
            files_response = requests.get(files_url, headers=headers)
            files_data = files_response.json()
            if files_response.status_code == 200:
                files_changed = [file['filename'] for file in files_data['files']]
                return files_changed, files_response.status_code 
            else:
                return None, files_response.status_code
    return None, response.status_code


def extract_github_repo_owner_name_from_link(url):
    """
    Get Github repository owner name and the name of the repository.
    
    Parameters
    ----------
    url : str
        URL of a GitHub repository.

    Returns
    -------
    tuple
        Tuple with GitHub repository owner and name.
    """
    repo_owner, repo_name = "", ""
    # Verify the link start with http:// or https://
    # to extract the right columns later.
    if url.startswith("http://") or url.startswith("https://"):
        url_fields = str(url).split("/")
        if len(url_fields) >= 4:
            repo_owner = url_fields[3]
        if len(url_fields) >= 5:
            repo_name = url_fields[4].strip()
    return repo_owner, repo_name


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
    
    headers = {"Authorization": f"Token {token}"}
    owner, repo = extract_github_repo_owner_name_from_link(url)
    query = f"https://api.github.com/repos/{owner}/{repo}"
    wait_time = 0.75  # max 5000 requests / hour = 1 request / 0.72 second
    info = {"date_repo_created": None, "date_repo_updated": None, "is_fork": None}
    response = requests.get(query, headers=headers)
    if response.status_code != 200:
        record_api_error(query=query,
                         attempt=1,
                         response=response,
                         output_name=log_name,
                         append_log=True
                        )
        print(f"ERROR with query: {query}")
    else:
        repository_info = response.json()
        info["is_fork"] = repository_info["fork"]
        info["date_repo_created"] = repository_info["created_at"].split("T")[0]
        info["date_repo_updated"] = repository_info["updated_at"].split("T")[0]
    # Wait to avoid rate limit
    time.sleep(wait_time)
    return info


############################################################################################
####################################----SOFTWH----##########################################
############################################################################################

def check_repository_is_archived_in_swh(url):
    """
    Get Software Heritage repository info.
    
    Example of GitHub repository archived in Software Heritage:
    - url: https://github.com/jupyterlite/jupyterlite/
    - API: https://archive.softwareheritage.org/api/1/origin/https://github.com/jupyterlite/jupyterlite/visit/latest/
    
    Example of GitHub repository not archived in Software Heritage:
    - url: https://github.com/pierrepo/blabla/
    - API: https://archive.softwareheritage.org/api/1/origin/https://github.com/pierrepo/blabla/visit/latest/

    Parameters
    ----------
    url : str
        URL of the GitHub repository.

    Returns
    -------
    dict
        Dictionnary with archive status and date of last archive.
    """
    info = {"is_archived": False, "date_archived": None}
    query = f"https://archive.softwareheritage.org/api/1/origin/{url}visit/latest/"
    response = requests.get(query)
    if response.status_code == 200:
        info["is_archived"] = True
        info["date_archived"] = response.json()["date"].split("T")[0]
    return info
