"""Translates a selected PICO into a PubMed search query string."""

import xml.etree.ElementTree as ET


def build_search_query(pico):
    return f"""{pico["population"]} AND {pico["intervention"]} AND (Randomized Controlled Trial[pt] OR Systematic Review[pt])"""


def search_pubmed(query, http_get):
    response = http_get(query)
    try:
        return response["esearchresult"]["idlist"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"Malformed PubMed search response: {response!r}") from e


def fetch_abstracts(pmids, http_get):
    response = http_get(pmids)
    return response


def parse_pubmed_xml(xml_text):
    root = ET.fromstring(xml_text)
    records = []

    for article in root.findall(".//PubmedArticle"):
        records.append(
            {
                "pmid": article.find(".//PMID").text,
                "title": article.find(".//ArticleTitle").text,
                "text": article.find(".//AbstractText").text,
                "publication_type": article.find(".//PublicationType").text,
                "publication_date": article.find(".//PubDate/Year").text,
            }
        )
    return records
