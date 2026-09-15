"""Translates a selected PICO into a PubMed search query string."""


def build_search_query(pico):
    return f"""{pico["population"]} AND {pico["intervention"]} AND (Randomized Controlled Trial[pt] OR Systematic Review[pt])"""


def search_pubmed(query, http_get):
    response = http_get(query)
    try:
        return response["esearchresult"]["idlist"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"Malformed PubMed search response: {response!r}") from e
