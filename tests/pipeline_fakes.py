"""Shared pipeline fakes and fixed responses for tests that run the pipeline on fakes."""

VALID_PICO_RESPONSE = (
    '[{"population": "adults with type 2 diabetes", "intervention": "metformin", '
    '"comparison": "sulfonylurea", "outcome": "HbA1c reduction"}, '
    '{"population": "adults with type 2 diabetes", "intervention": "lifestyle modification", '
    '"comparison": "metformin", "outcome": "weight loss"}]'
)

VALID_SEARCH_TERMS_RESPONSE = (
    '{"population_terms": "type 2 diabetes mellitus", "intervention_terms": "metformin"}'
)

VALID_SUMMARY = (
    "Evidence Summary: Metformin lowered HbA1c more than sulfonylurea "
    "(PMID: 1234567). This is not a diagnosis or treatment recommendation."
)

VALID_XML = """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1234567</PMID>
      <Article>
        <ArticleTitle>Metformin versus sulfonylurea in type 2 diabetes</ArticleTitle>
        <Abstract>
          <AbstractText>A randomized trial comparing HbA1c reduction between metformin and sulfonylurea.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2020</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


def scripted_model_call(responses):
    remaining = list(responses)

    def _model_call(prompt):
        return remaining.pop(0)

    return _model_call


def routing_model_call(
    pico_response=VALID_PICO_RESPONSE,
    summary_response=VALID_SUMMARY,
    search_terms_response=VALID_SEARCH_TERMS_RESPONSE,
):
    def _model_call(prompt):
        if "Now extract PICO candidates" in prompt:
            return pico_response
        if "medical librarian" in prompt:
            return search_terms_response
        return summary_response

    return _model_call
