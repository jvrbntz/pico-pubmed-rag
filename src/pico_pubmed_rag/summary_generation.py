"""Generates a PMID-cited evidence summary from ranked abstracts via an injected LLM call."""


def build_summary_prompt(pico, abstracts):
    formatted_abstracts = "\n\n".join(
        f"PMID: {a['pmid']}\nTitle: {a['title']}\nText: {a['text']}" for a in abstracts
    )

    return f"""
    You are a clinical evidence specialist who synthesizes findings from published literature to answer a specific clinical question, without offering a diagnosis or treatment recommendation for any individual patient.

    Using only the abstracts provided below, write a summary that answers the given PICO question. Follow these rules:
    - Base every claim strictly on the provided abstracts. Do not introduce outside knowledge or assumptions.
    - Cite the PMID immediately after each claim it supports, in the format (PMID: 12345678).
    - Begin the summary with the label "Evidence Summary:" and explicitly state that this is not a diagnosis or treatment recommendation.
    - If none of the abstracts clearly support an answer, do not guess or force a citation. Instead, begin your response with "No Clear Answer:" and explain why the abstracts don't answer the question. Use only one of these two labels, never both.

    Here's the PICO:
    {pico}

    Here are the abstracts:
    {formatted_abstracts}
"""


MAX_ATTEMPTS = 2


def generate_summary(pico, abstracts, llm_call):
    if not abstracts:
        raise ValueError("Cannot generate a summary with no abstracts to cite")

    prompt = build_summary_prompt(pico, abstracts)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = llm_call(prompt)

        if "<unused95>" in response:
            response = response.split("<unused95>", 1)[1].strip()

        has_label = "Evidence Summary:" in response
        has_pmid = any(a["pmid"] in response for a in abstracts)
        is_no_clear_answer = "No Clear Answer:" in response

        if is_no_clear_answer:
            return response

        if has_label and has_pmid:
            return response

        if attempt == MAX_ATTEMPTS:
            if not has_label:
                raise ValueError(f"Summary missing required self-label: {response!r}")
            raise ValueError(
                f"Summary contains no PMID citation from the given abstracts: {response!r}"
            )
