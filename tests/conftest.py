"""Shared fixtures for tests that run the pipeline on fakes."""

import pytest

from tests.pipeline_fakes import VALID_XML


@pytest.fixture
def search_call_strict_hits():
    def _search_call(query):
        return {"esearchresult": {"idlist": ["1234567", "2345678", "3456789"]}}

    return _search_call


@pytest.fixture
def fetch_call_valid_xml():
    def _fetch_call(pmids):
        return VALID_XML

    return _fetch_call
