"""Acceptance-criteria tests for build_search_query, search_pubmed, fetch_abstracts, and parse_pubmed_xml in pubmed_search.py."""

import pytest

from pico_pubmed_rag.pubmed_search import (
    ConfigurationError,
    build_search_query,
    efetch_get,
    esearch_get,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed,
    search_pubmed_with_broadening,
)


@pytest.fixture
def sample_search_terms():
    return {"population_terms": "streptococcal pharyngitis", "intervention_terms": "amoxicillin"}


@pytest.fixture
def fake_http_get():
    def _fake_http_get(query):
        return {"esearchresult": {"idlist": ["12345", "23456", "34567"]}}

    return _fake_http_get


@pytest.fixture
def empty_http_get():
    def _empty_http_get(query):
        return {"esearchresult": {"idlist": []}}

    return _empty_http_get


@pytest.fixture
def malformed_http_get():
    def _malformed_http_get(query):
        return {"esearchresult": "some_error"}

    return _malformed_http_get


@pytest.fixture
def fake_efetch_get():
    def _fake_efetch_get(pmids):
        return "<PubmedArticleSet>...</PubmedArticleSet>"

    return _fake_efetch_get


@pytest.fixture
def sample_pubmed_xml():
    return """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Amoxicillin versus penicillin for strep throat</ArticleTitle>
        <Abstract>
          <AbstractText>A randomized trial comparing outcomes between amoxicillin and penicillin.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2019</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>23456789</PMID>
      <Article>
        <ArticleTitle>Watchful waiting versus antibiotics for strep throat</ArticleTitle>
        <Abstract>
          <AbstractText>A systematic review of watchful waiting versus immediate antibiotic treatment.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Systematic Review</PublicationType>
        </PublicationTypeList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2021</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


@pytest.fixture
def http_get_needs_broadening():
    def _http_get_needs_broadening(query):
        if "[pt]" in query:
            return {"esearchresult": {"idlist": []}}
        return {"esearchresult": {"idlist": ["12345", "23456"]}}

    return _http_get_needs_broadening


def test_build_search_query_returns_string(sample_search_terms):
    result = build_search_query(sample_search_terms)
    assert isinstance(result, str)


def test_build_search_query_uses_the_search_terms(sample_search_terms):
    result = build_search_query(sample_search_terms)
    assert sample_search_terms["population_terms"] in result
    assert sample_search_terms["intervention_terms"] in result


def test_build_search_query_joins_search_terms_with_and(sample_search_terms):
    result = build_search_query(sample_search_terms)
    assert result.startswith("streptococcal pharyngitis AND amoxicillin")


def test_build_search_query_includes_publication_type_filter(sample_search_terms):
    result = build_search_query(sample_search_terms)
    assert "(Randomized Controlled Trial[pt] OR Systematic Review[pt])" in result


def test_search_pubmed_returns_list_of_pmids(fake_http_get):
    result = search_pubmed("some query", fake_http_get)
    assert result == ["12345", "23456", "34567"]


def test_search_pubmed_returns_empty_pmids_list(empty_http_get):
    result = search_pubmed("some_query", empty_http_get)
    assert result == []


def test_search_pubmed_returns_malformed_response(malformed_http_get):
    with pytest.raises(ValueError):
        search_pubmed("some_query", malformed_http_get)


def test_fetch_abstracts_returns_http_get_result(fake_efetch_get):
    result = fetch_abstracts(["12345"], fake_efetch_get)
    assert result == "<PubmedArticleSet>...</PubmedArticleSet>"


def test_parse_pubmed_xml_returns_one_entry_per_article(sample_pubmed_xml):
    result = parse_pubmed_xml(sample_pubmed_xml)
    assert len(result) == 2


def test_parse_pubmed_xml_returns_correct_keys(sample_pubmed_xml):
    result = parse_pubmed_xml(sample_pubmed_xml)
    for record in result:
        assert set(record.keys()) == {
            "pmid",
            "title",
            "text",
            "publication_type",
            "publication_date",
        }


def test_parse_pubmed_xml_returns_correct_values(sample_pubmed_xml):
    result = parse_pubmed_xml(sample_pubmed_xml)
    assert result[0]["pmid"] == "12345678"
    assert result[0]["title"] == "Amoxicillin versus penicillin for strep throat"
    assert (
        result[0]["text"]
        == "A randomized trial comparing outcomes between amoxicillin and penicillin."
    )
    assert result[0]["publication_type"] == [
        "Randomized Controlled Trial",
        "Journal Article",
    ]
    assert result[0]["publication_date"] == "2019"


def test_search_pubmed_with_broadening_returns_results_from_broadening_query(
    http_get_needs_broadening,
):
    result = search_pubmed_with_broadening(
        "search_terms AND (Randomized Controlled Trial[pt] OR Systematic Review[pt])",
        http_get_needs_broadening,
    )
    assert result == ["12345", "23456"]


def test_esearch_get_raises_configuration_error_without_ncbi_settings(monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    with pytest.raises(ConfigurationError):
        esearch_get("metformin")


def test_efetch_get_raises_configuration_error_without_ncbi_settings(monkeypatch):
    monkeypatch.delenv("NCBI_TOOL_NAME", raising=False)
    with pytest.raises(ConfigurationError):
        efetch_get(["1234567"])
