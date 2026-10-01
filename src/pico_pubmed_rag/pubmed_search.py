"""Builds a PubMed query from a selected PICO, searches and fetches through NCBI E-utilities with zero-result broadening, and parses fetched records into abstracts."""

import os
import xml.etree.ElementTree as ET

import requests


class ConfigurationError(ValueError):
    """Raised when required NCBI settings are missing from the environment."""


PUBLICATION_TYPE_FILTER = " AND (Randomized Controlled Trial[pt] OR Systematic Review[pt])"


def build_search_query(pico):
    return f"""{pico["population"]} AND {pico["intervention"]}{PUBLICATION_TYPE_FILTER}"""


def search_pubmed(query, http_get):
    response = http_get(query)
    try:
        return response["esearchresult"]["idlist"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"Malformed PubMed search response: {response!r}") from e


def search_pubmed_with_broadening(query, http_get):
    results = search_pubmed(query, http_get)
    if not results:
        broadened_query = query.replace(PUBLICATION_TYPE_FILTER, "")
        results = search_pubmed(broadened_query, http_get)
    return results


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
                "publication_type": [
                    pt.text for pt in article.findall(".//PublicationType")
                ],
                "publication_date": article.find(".//PubDate/Year").text,
            }
        )
    return records


def esearch_get(query):
    tool = os.environ.get("NCBI_TOOL_NAME")
    email = os.environ.get("NCBI_EMAIL")
    if not tool or not email:
        raise ConfigurationError(
            "NCBI_TOOL_NAME and NCBI_EMAIL must be set. Copy .env.example to .env and fill it in."
        )

    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "tool": tool,
        "email": email,
    }
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]

    response = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params
    )
    return response.json()


def efetch_get(pmids):
    tool = os.environ.get("NCBI_TOOL_NAME")
    email = os.environ.get("NCBI_EMAIL")
    if not tool or not email:
        raise ConfigurationError(
            "NCBI_TOOL_NAME and NCBI_EMAIL must be set. Copy .env.example to .env and fill it in."
        )

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "tool": tool,
        "email": email,
    }
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]

    response = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=params
    )
    return response.text
