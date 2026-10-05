"""Streamlit app for reviewing one batch's runs, one per screen, and saving the reviewer's annotations next to the batch file.

Run: uv run streamlit run scripts/review_app.py -- runs/<batch file> --outcome completed
"""

import argparse
import re
from pathlib import Path

import streamlit as st

from pico_pubmed_rag.review import (
    build_review_queue,
    build_run_view,
    load_annotations,
    review_progress,
    save_annotation,
    unannotated_runs,
)
from pico_pubmed_rag.trace_file import read_traces

MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~:$])")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_file")
    parser.add_argument("--outcome", default="completed", choices=["completed", "no_evidence", "failed"])
    return parser.parse_args()


@st.cache_data
def load_queue(batch_file, outcome):
    return build_review_queue(read_traces(batch_file), outcome)


def escape(text):
    return MARKDOWN_SPECIAL.sub(r"\\\1", str(text))


def highlighted_summary(view):
    text = escape(view["summary"])
    for label in view["labels"]:
        text = text.replace(escape(label), f"**{escape(label)}**")
    for pmid in view["cited_pmids"]:
        colour = "red" if pmid in view["unshown_cited_pmids"] else "blue"
        text = text.replace(pmid, f":{colour}[**{pmid}**]")
    return text


def save_from_widgets(annotation_path, run_id, case_id):
    save_annotation(
        annotation_path,
        run_id=run_id,
        case_id=case_id,
        answerable=st.session_state[f"answerable-{run_id}"],
        summary_verdict=st.session_state[f"verdict-{run_id}"],
        notes=st.session_state[f"notes-{run_id}"],
        deferred=st.session_state[f"deferred-{run_id}"],
    )


def show_run(view, annotation, annotation_path):
    header = view["header"]
    run_id = header["run_id"]
    st.markdown(
        f"### Case {header['case_id']} · repeat {header['repeat']}  \n"
        f"{escape(header['specialty'])} · {escape(header['description'])}"
    )
    st.caption(f"run {run_id}")
    with st.expander("Full note"):
        st.text(view["note"])

    st.subheader("Clinical question")
    pico = view["pico"] or {}
    for field in ("population", "intervention", "comparison", "outcome"):
        st.markdown(f"**{field.capitalize()}:** {escape(pico.get(field) or 'none stated')}")
    terms = view["search_terms"]
    terms_text = (
        f"{escape(terms['population_terms'])} · {escape(terms['intervention_terms'])}" if terms else "none (version 1 trace)"
    )
    st.markdown(f"**Search terms:** {terms_text}")
    st.markdown(f"**Query sent:** `{view['query_sent'] or 'none'}`")

    st.subheader(f"Abstracts shown to the model ({len(view['abstracts'])})")
    for abstract in view["abstracts"]:
        types = ", ".join(abstract.get("publication_type") or [])
        st.markdown(
            f"**{escape(abstract.get('title', ''))}**  \n"
            f"PMID {abstract['pmid']} · {escape(types)} · {abstract.get('publication_date', '')}"
        )
        with st.expander("Abstract text"):
            st.text(abstract.get("text", ""))

    st.subheader("Summary")
    with st.container(border=True):
        st.markdown(highlighted_summary(view))
    if view["unshown_cited_pmids"]:
        st.error(f"Cites PMIDs that were not shown to the model: {', '.join(view['unshown_cited_pmids'])}")

    st.subheader("Your judgment")
    annotation = annotation or {}
    save = lambda: save_from_widgets(annotation_path, run_id, header["case_id"])
    st.radio("Could these abstracts answer the question?", ["yes", "no"], horizontal=True,
             index=["yes", "no"].index(annotation["answerable"]) if annotation.get("answerable") else None,
             key=f"answerable-{run_id}", on_change=save)
    st.radio("Was the summary's decision right?", ["pass", "fail"], horizontal=True,
             index=["pass", "fail"].index(annotation["summary_verdict"]) if annotation.get("summary_verdict") else None,
             key=f"verdict-{run_id}", on_change=save)
    st.text_area("Notes: what went wrong, in one sentence", value=annotation.get("notes", ""),
                 key=f"notes-{run_id}", on_change=save)
    st.checkbox("Defer (come back to this one)", value=annotation.get("deferred", False),
                key=f"deferred-{run_id}", on_change=save)

    with st.expander("Raw model responses (debugging)"):
        for stage_name, responses in view.get("raw_responses", {}).items():
            st.caption(stage_name)
            for response in responses:
                st.code(response, language=None)


def main():
    args = parse_args()
    st.set_page_config(page_title="Trace review", layout="wide")
    batch_path = Path(args.batch_file)
    annotation_path = batch_path.with_name(f"annotations_{batch_path.stem}.json")

    queue = load_queue(str(batch_path), args.outcome)
    annotations = load_annotations(annotation_path)
    progress = review_progress(queue, annotations)

    with st.sidebar:
        st.title("Trace review")
        st.caption(f"{batch_path.name} · {args.outcome} runs")
        st.metric("Annotated", f"{progress['annotated']} / {len(queue)}")
        st.write(f"Deferred: {progress['deferred']} · Unannotated: {progress['unannotated']}")
        only_unannotated = st.toggle("Show only unannotated")
        runs = unannotated_runs(queue, annotations) if only_unannotated else queue
        case_ids = sorted({t["case_id"] for t in runs})
        jump = st.selectbox("Jump to case", ["(none)"] + case_ids)

    if not runs:
        st.success("Nothing left to review in this view.")
        return

    position = st.session_state.get("position", 0)
    if jump != "(none)" and st.session_state.get("last_jump") != jump:
        position = next(i for i, t in enumerate(runs) if t["case_id"] == jump)
        st.session_state["last_jump"] = jump
    position = min(position, len(runs) - 1)

    previous, counter, following = st.columns([1, 3, 1])
    if previous.button("← Previous", disabled=position == 0):
        position -= 1
    if following.button("Next →", disabled=position == len(runs) - 1):
        position += 1
    st.session_state["position"] = position
    counter.markdown(f"**Run {position + 1} of {len(runs)}**")

    trace = runs[position]
    show_run(build_run_view(trace), annotations.get(trace["run_id"]), annotation_path)


main()
