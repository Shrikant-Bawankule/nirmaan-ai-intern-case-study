# app.py
import io
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union

import streamlit as st
import pandas as pd

# third-party parsers
import PyPDF2
import docx

# project modules (must exist in project root)
from rubric_loader import load_rubric
from scoring_logic import score_transcript

# constants: project-relative files
RUBRIC_FILE = Path("Case study for interns.xlsx")
SAMPLE_FILE = Path("Sample text for case study.txt")

st.set_page_config(page_title="Nirmaan AI — Communication Scorer", layout="wide")

# minimal dark CSS for neat output
CSS = """
<style>
body, .stApp { background-color: #0f1113; color: #e6e6e6; }
.section-card { background: #0f1113; border-radius: 10px; padding: 16px; border: 1px solid rgba(255,255,255,0.04); }
textarea, .stTextArea textarea { background: #151719 !important; color: #e6e6e6 !important; border-radius: 8px; }
.stButton>button { background: linear-gradient(180deg,#1f8aa5,#16707f); color: white; border-radius: 8px; padding: 8px 12px; }
.stat-box { background: #111316; border-radius: 8px; padding: 10px; border: 1px solid rgba(255,255,255,0.03); text-align:center; }
.json-box { background: #0b0c0d; border-radius: 8px; padding: 12px; color: #d6d6d6; font-family: monospace; max-height: 480px; overflow:auto; border: 1px solid rgba(255,255,255,0.03); }
.small-muted { color: #bfc7cc; font-size:0.95rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("Nirmaan AI — Communication Scorer")
st.write("Paste text, upload files (txt/pdf/docx), or use the sample. Scores are rubric-based with optional semantic signals.")

# load rubric (project relative)
try:
    rubric = load_rubric(RUBRIC_FILE if RUBRIC_FILE.exists() else None)
except Exception as e:
    st.error(f"Failed to load rubric: {e}")
    rubric = None

left_col, right_col = st.columns([2.6, 1])

with right_col:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("Rubric")
    if rubric:
        st.write(f"Loaded {len(rubric)} criteria.")
        for r in rubric:
            name = r.get("criterion", "Unnamed")
            weight = r.get("weight", 0.0)
            st.markdown(f"**{name}** (weight {weight:.2f})")
    else:
        st.info("Rubric not found. Place 'Case study for interns.xlsx' in project root.")
    st.markdown("</div>", unsafe_allow_html=True)

with left_col:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("Input")

    input_mode = st.radio("Input method", ["Paste text", "Upload files", "Use sample (project file)"])

    transcript_text = ""
    uploaded_files = []

    if input_mode == "Paste text":
        transcript_text = st.text_area("Paste transcript here", height=260, value="")
    elif input_mode == "Upload files":
        uploaded_files = st.file_uploader(
            "Upload files (txt, pdf, docx). You may select multiple files.",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=True
        )
    else:  # sample
        if SAMPLE_FILE.exists():
            transcript_text = SAMPLE_FILE.read_text(encoding="utf-8", errors="replace")
            transcript_text = st.text_area("Sample transcript (editable)", value=transcript_text, height=260)
        else:
            transcript_text = st.text_area("Sample transcript (editable)", value="Sample file not found.", height=260)

    mode = st.radio("Scoring mode", ["Score single transcript (paste/sample)", "Score uploaded files individually", "Combine uploaded files and score as one transcript"])

    run_score = st.button("Score")

    st.markdown("</div>", unsafe_allow_html=True)

    # helpers for extraction
    def extract_text_from_pdf_stream(stream: io.BytesIO) -> str:
        try:
            reader = PyPDF2.PdfReader(stream)
            pages = []
            for p in reader.pages:
                text = p.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
        except Exception:
            try:
                return stream.getvalue().decode("utf-8", errors="replace")
            except Exception:
                return ""

    def extract_text_from_docx_stream(stream: io.BytesIO) -> str:
        try:
            doc = docx.Document(stream)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            try:
                return stream.getvalue().decode("utf-8", errors="replace")
            except Exception:
                return ""

    def extract_text_from_uploaded(uploaded) -> Tuple[str, str]:
        name = uploaded.name
        suffix = Path(name).suffix.lower()
        raw = uploaded.getvalue()
        stream = io.BytesIO(raw)
        if suffix == ".txt":
            try:
                return raw.decode("utf-8"), name
            except Exception:
                return raw.decode("latin-1", errors="replace"), name
        if suffix == ".pdf":
            return extract_text_from_pdf_stream(stream), name
        if suffix == ".docx":
            return extract_text_from_docx_stream(stream), name
        # fallback
        try:
            return raw.decode("utf-8"), name
        except Exception:
            return raw.decode("latin-1", errors="replace"), name

    def compute_stats(text: str) -> Dict[str, int]:
        words = len([w for w in text.split() if w.strip()])
        chars = len(text)
        sentences = max(0, len([s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]))
        return {"words": words, "chars": chars, "sentences": sentences}

    # perform scoring based on selected mode
    results: List[Dict[str, Any]] = []

    if run_score:
        if mode == "Score single transcript (paste/sample)":
            if not transcript_text or not transcript_text.strip():
                st.warning("Please provide transcript text.")
            else:
                try:
                    res = score_transcript(transcript_text, rubric, duration_sec=None)
                    res_struct = {
                        "filename": "pasted_input" if input_mode == "Paste text" else "sample_file",
                        "overall_score": res.get("overall_score"),
                        "per_criterion": res.get("per_criterion"),
                        "words": res.get("words")
                    }
                    results.append(res_struct)
                except Exception as e:
                    st.error(f"Scoring failed: {e}")
        else:
            if not uploaded_files:
                st.warning("Please upload one or more files.")
            else:
                extracted_list: List[Tuple[str, str]] = []
                for uf in uploaded_files:
                    text, name = extract_text_from_uploaded(uf)
                    extracted_list.append((name, text))

                if mode == "Score uploaded files individually":
                    for name, text in extracted_list:
                        if not text.strip():
                            st.warning(f"No extractable text in {name}. Skipping.")
                            continue
                        try:
                            res = score_transcript(text, rubric, duration_sec=None)
                            results.append({
                                "filename": name,
                                "overall_score": res.get("overall_score"),
                                "per_criterion": res.get("per_criterion"),
                                "words": res.get("words")
                            })
                        except Exception as e:
                            st.error(f"Scoring failed for {name}: {e}")
                else:  # combine and score
                    combined_text = "\n\n".join([t for (_, t) in extracted_list if t.strip()])
                    if not combined_text.strip():
                        st.warning("Combined content is empty.")
                    else:
                        try:
                            res = score_transcript(combined_text, rubric, duration_sec=None)
                            results.append({
                                "filename": "combined_upload",
                                "overall_score": res.get("overall_score"),
                                "per_criterion": res.get("per_criterion"),
                                "words": res.get("words")
                            })
                        except Exception as e:
                            st.error(f"Scoring failed for combined upload: {e}")

    # display results
    if results:
        st.success("Scoring complete")
        for r in results:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.subheader(f"Result — {r.get('filename')}")
            st.markdown(f"**Overall score:** {r.get('overall_score', 0.0):.2f} / 100")
            per = r.get("per_criterion", [])
            # show table
            rows = []
            for p in per:
                rows.append({
                    "criterion": p.get("criterion"),
                    "weight": p.get("weight"),
                    "combined_score": round(p.get("combined_score", 0.0), 2),
                    "weighted_contribution": round(p.get("weighted_contribution", 0.0), 6),
                    "raw_points": p.get("raw_points")
                })
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, height=240)
            # pretty JSON output
            pretty = json.dumps(r, indent=2, ensure_ascii=False)
            st.markdown("<div class='json-box'>", unsafe_allow_html=True)
            st.markdown(f"<pre>{pretty}</pre>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            # download button
            json_bytes = pretty.encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_bytes,
                file_name=f"{r.get('filename')}_scoring.json",
                mime="application/json"
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # quick stats when nothing scored yet (live preview of pasted/sample)
    if not results and input_mode in ("Paste text", "Use sample (project file)"):
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("Quick Stats")
        stats = compute_stats(transcript_text or "")
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['words']}</strong><div class='small-muted'>Word Count</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['chars']}</strong><div class='small-muted'>Characters</div></div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        c3.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>-</strong><div class='small-muted'>Words/Min</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['sentences']}</strong><div class='small-muted'>Sentences</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
