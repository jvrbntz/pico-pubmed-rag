"""Streamlit app for judging abstracts on a relevance sheet, one per screen, saving one yes/no label per case and PMID next to the sheet.

Run: uv run streamlit run scripts/relevance_app.py -- runs/<sheet file>.csv
"""

import argparse
import re
from pathlib import Path

import streamlit as st

from pico_pubmed_rag.relevance import (
    labeling_progress,
    load_labels,
    load_sheet,
    next_unlabeled,
    save_label,
)

MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~:$])")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet_file")
    return parser.parse_args()


def escape(text):
    return MARKDOWN_SPECIAL.sub(r"\\\1", str(text))


def label_and_advance(labels_path, items, position, relevant):
    item = items[position]
    notes = st.session_state.get(f"notes-{item['case_id']}-{item['pmid']}", "")
    save_label(labels_path, item["case_id"], item["pmid"], relevant, notes)
    remaining = next_unlabeled(items[position + 1:], load_labels(labels_path))
    if remaining is not None:
        st.session_state["position"] = position + 1 + remaining
    else:
        st.session_state["position"] = min(position + 1, len(items) - 1)


def go_back(position):
    st.session_state["position"] = max(position - 1, 0)


def show_item(item, label, labels_path, items, position):
    st.markdown(f"### Case {item['case_id']}  \n{escape(item.get('note_description', ''))}")
    with st.container(border=True):
        st.markdown(f"**Clinical question:** {escape(item['pico'])}")

    st.subheader(escape(item["title"]))
    st.caption(f"PMID {item['pmid']} · {item.get('publication_type', '')} · {item.get('year', '')}")
    st.markdown(escape(item["abstract"]).replace("\n", "  \n"))

    st.divider()
    if label:
        st.info(f"Labeled {label['relevant']} on {label['judged_on']}. Clicking again replaces it.")
    st.text_area(
        "Notes (optional)",
        value=(label or {}).get("notes", ""),
        key=f"notes-{item['case_id']}-{item['pmid']}",
    )
    back, yes, no = st.columns([1, 2, 2])
    back.button("← Back", disabled=position == 0, on_click=go_back, args=(position,))
    yes.button("Relevant: yes", type="primary", on_click=label_and_advance,
               args=(labels_path, items, position, "yes"))
    no.button("Relevant: no", on_click=label_and_advance,
              args=(labels_path, items, position, "no"))


def main():
    args = parse_args()
    st.set_page_config(page_title="Relevance labeling", layout="centered")
    sheet_path = Path(args.sheet_file)
    labels_path = sheet_path.with_name(f"relevance_labels_{sheet_path.stem}.jsonl")

    items = load_sheet(sheet_path)
    labels = load_labels(labels_path)
    labeled, total = labeling_progress(items, labels)

    with st.sidebar:
        st.title("Relevance labeling")
        st.caption(sheet_path.name)
        st.metric("Labeled", f"{labeled} / {total}")
        st.caption(
            "Relevant: the abstract studies the question's population and intervention, "
            "and reports the comparison or the outcome."
        )

    if "position" not in st.session_state:
        first = next_unlabeled(items, labels)
        st.session_state["position"] = first if first is not None else 0
    position = st.session_state["position"]

    if labeled == total:
        st.success("Every abstract on this sheet is labeled.")
    st.markdown(f"**Abstract {position + 1} of {total}**")
    item = items[position]
    show_item(item, labels.get((item["case_id"], item["pmid"])), labels_path, items, position)


main()
