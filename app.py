import streamlit as st
import pandas as pd
import json
from pathlib import Path

# local project files (relative)
RUBRIC_XLSX = Path("Case study for interns.xlsx")
SAMPLE_TXT = Path("Sample text for case study.txt")

# import project modules
from rubric_loader import load_rubric
from scoring_logic import score_transcript

st.set_page_config(page_title="Nirmaan AI — Communication Scorer", layout="wide")

# CSS (dark minimal)
CSS = """
<style>
body, .stApp { background-color: #0f1113; color: #e6e6e6; }
.section-card { background: #0f1113; border-radius: 12px; padding: 18px; border: 1px solid rgba(255,255,255,0.03); }
textarea, .stTextArea textarea { background: #151719 !important; color: #e6e6e6 !important; border-radius: 8px; }
.stButton>button { background: linear-gradient(180deg, #1f8aa5, #16707f); color: white; border-radius: 10px; }
.stat-box { background: #111316; border-radius: 10px; padding: 12px; border: 1px solid rgba(255,255,255,0.03); }
.json-box { background: #0b0c0d; border-radius: 8px; padding: 12px; color: #d6d6d6; font-family: monospace; max-height: 420px; overflow:auto; border: 1px solid rgba(255,255,255,0.03); }
.small-muted { color: #bfc7cc; font-size: 0.95rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Header
st.title("Nirmaan AI — Communication Scorer (Case Study)")
st.write("Paste transcript text or upload a .txt file. Uses rule-based + semantic scoring.")

left, right = st.columns([2.6, 1])

# Rubric panel
with right:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("Rubric")
    try:
        rubric = load_rubric(RUBRIC_XLSX if RUBRIC_XLSX.exists() else None)
    except Exception as e:
        rubric = None
        st.error(f"Error loading rubric: {e}")
    if rubric:
        st.write(f"Loaded {len(rubric)} criteria.")
        for r in rubric:
            name = r.get("criterion", "Unnamed")
            weight = r.get("weight", 0.0)
            st.markdown(f"**{name}** (weight {weight:.2f})")
    else:
        st.info("Rubric not found. Place rubric file in project root.")
    st.markdown("</div>", unsafe_allow_html=True)

# Input + scoring UI
with left:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("Input Transcript")

    method = st.radio("Input method", ("Paste text", "Upload .txt", "Use sample text (provided)"))

    transcript = ""
    uploaded = None
    if method == "Paste text":
        transcript = st.text_area("Paste transcript here", height=260, value="")
    elif method == "Upload .txt":
        uploaded = st.file_uploader("Upload text (.txt)", type=["txt"])
        if uploaded:
            try:
                transcript = uploaded.getvalue().decode("utf-8")
            except Exception:
                transcript = uploaded.getvalue().decode("latin-1", errors="replace")
    else:
        if SAMPLE_TXT.exists():
            transcript = SAMPLE_TXT.read_text(encoding="utf-8", errors="replace")
        else:
            transcript = "Hello everyone, myself Muskan..."

    evaluate = st.button("Score")

    st.markdown("</div>", unsafe_allow_html=True)

    # quick stats
    def compute_stats(text: str):
        words = len([w for w in text.split() if w.strip()])
        chars = len(text)
        sentences = max(0, len([s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]))
        return {"words": words, "chars": chars, "sentences": sentences}

    stats = compute_stats(transcript or "")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("Quick Stats")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['words']}</strong><div class='small-muted'>Word Count</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['chars']}</strong><div class='small-muted'>Characters</div></div>", unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>-</strong><div class='small-muted'>Words/Min</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='stat-box'><strong style='font-size:1.25rem'>{stats['sentences']}</strong><div class='small-muted'>Sentences</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # scoring
    result = None
    if evaluate:
        if not transcript.strip():
            st.warning("Please provide a transcript to score.")
        else:
            try:
                result = score_transcript(transcript, rubric, duration_sec=None)
            except Exception as e:
                st.exception(e)
                result = None

    if result:
        st.success(f"Overall score: {result.get('overall_score', 0.0):.2f} / 100")
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("Scores — per criterion")
        per = result.get("per_criterion", [])
        rows = []
        for p in per:
            rows.append({
                "criterion": p.get("criterion"),
                "weight": p.get("weight"),
                "combined_score": round(p.get("combined_score", 0.0), 2),
                "weighted_contribution": round(p.get("weighted_contribution", 0.0), 6),
                "rule_score": round(p.get("rule_score", 0.0), 2) if p.get("rule_score") is not None else None,
                "semantic_score": round(p.get("semantic_score", 0.0), 2) if p.get("semantic_score") is not None else None,
                "raw_points": p.get("raw_points"),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, height=280)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Detailed JSON Output")
        st.markdown(f"<div class='json-box'>{json.dumps(result, indent=2)[:10000]}</div>", unsafe_allow_html=True)
        st.download_button("Download JSON", data=json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name="scoring_result.json", mime="application/json")
