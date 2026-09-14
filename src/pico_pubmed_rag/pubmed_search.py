"""Translates a selected PICO into a PubMed search query string."""


def build_search_query(pico):
    return f"""{pico["population"]} AND {pico["intervention"]} AND (Randomized Controlled Trial[pt] OR Systematic Review[pt])"""
