"""Acceptance-criteria tests for build_search_query, search_pubmed, fetch_abstracts, and parse_pubmed_xml in pubmed_search.py."""

import pytest

from pico_pubmed_rag.pubmed_search import (
    build_search_query,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed,
)


@pytest.fixture
def sample_pico():
    return {
        "population": "adults with strep throat",
        "intervention": "amoxicillin",
        "comparison": "penicillin",
        "outcome": "symptom resolution",
    }


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


def test_build_search_query_returns_string(sample_pico):
    result = build_search_query(sample_pico)
    assert isinstance(result, str)


def test_build_search_query_includes_population_and_intervention(sample_pico):
    result = build_search_query(sample_pico)
    assert sample_pico["population"] in result
    assert sample_pico["intervention"] in result


def test_build_search_query_joins_population_and_intervention_with_and(sample_pico):
    result = build_search_query(sample_pico)
    assert f"{sample_pico['population']} AND {sample_pico['intervention']}" in result


def test_build_search_query_includes_publication_type_filter(sample_pico):
    result = build_search_query(sample_pico)
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
    assert result[0]["publication_type"] == "Randomized Controlled Trial"
    assert result[0]["publication_date"] == "2019"
