from Bio import Entrez
import re

def get_abstract(PMID): 
    
    handle = Entrez.efetch(db = "pubmed", id = PMID)
    record = Entrez.read(handle)
    nb_of_parts_in_abstract = len(record["PubmedArticle"][0]["MedlineCitation"]["Article"]["Abstract"]["AbstractText"])
    paragrafs = []
    for i in range(nb_of_parts_in_abstract):
        paragrafs.append(record["PubmedArticle"][0]["MedlineCitation"]["Article"]["Abstract"]["AbstractText"][i])
        abstract = " ".join(paragrafs)
        
    return abstract

def get_link(df, PMID):
    
    regex = ["https:\/[^ ]*[./]github.com[^ ,]*[^ ).]", "github.com[^ ,]*[^ ).]"]
    links_with_point = ''
    
    for rgx in regex:
        if (links_with_point == '') and re.search(rgx, str(df.loc[df["Id"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
                links_with_point = re.findall(rgx, str(df.loc[df["Id"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
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
            if link[-1] == ")" or link[-1] == "." or link[-1] == ",":
                link = link[:-1]
        links.append(link)
        
    return links

def get_phrase_with_link(df, PMID):
    
    regex = ["\.[^.]*[./]github[^ ]* [^.]*[^ ]*\.", "\.[^.]*[./]github[^ ]*", "[^.]*github[^ ]*", "[a-zA-Z0-9 .,/:\'\"!?]{101}github[^ ]*[a-zA-Z0-9 .,/:\'\"!?()]{100}"]
    phrase_with_point = ''
    
    for rgx in regex:
        if (phrase_with_point == "") and re.search(rgx, str(df.loc[df["Id"] == PMID, "Abstract"].values[0]), re.IGNORECASE):
            phrase_with_point = re.findall(rgx, str(df.loc[df["Id"] == PMID, "Abstract"].values[0]), re.IGNORECASE)
    phrases = []
    for phrase in phrase_with_point :
        phrase = phrase[2:]
        phrases.append(phrase)
        
    return ' '.join(phrases)