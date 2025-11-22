import re
import math
from typing import List, Dict, Any, Optional

# optional semantic model
try:
    from sentence_transformers import SentenceTransformer, util
    _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _ST_MODEL = None

# optional grammar tool
try:
    import language_tool_python
    _LT_TOOL = language_tool_python.LanguageTool('en-US')
except Exception:
    _LT_TOOL = None

# optional VADER sentiment
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
except Exception:
    _VADER = None

CRITERION_POINTS = {
    "Content & Structure": 40.0,
    "Speech Rate": 10.0,
    "Language & Grammar": 20.0,
    "Vocabulary Richness": 10.0,
    "Clarity": 15.0,
    "Engagement": 15.0
}

def tokenize_words(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())

def word_count(text: str) -> int:
    return len(tokenize_words(text))

def semantic_similarity_score(a: str, b: str) -> float:
    if not _ST_MODEL or not a.strip() or not b.strip():
        return 0.0
    emb_a = _ST_MODEL.encode(a, convert_to_tensor=True)
    emb_b = _ST_MODEL.encode(b, convert_to_tensor=True)
    sim = util.cos_sim(emb_a, emb_b).item()
    sim01 = (sim + 1.0) / 2.0
    return float(max(0.0, min(100.0, sim01 * 100.0)))

# Content & Structure helpers
SALUTATION_PHRASES = {
    "excellent": ["i am excited", "feeling great", "i am delighted", "i'm excited"],
    "good": ["good morning", "good afternoon", "good evening", "good day", "hello everyone"],
    "normal": ["hi", "hello"]
}
SALUTATION_MAP = {"no salulation": 0, "normal": 2, "good": 4, "excellent": 5}

def detect_salutation(text: str) -> Dict[str, Any]:
    t = text.lower()
    for level, phrases in SALUTATION_PHRASES.items():
        for p in phrases:
            if p in t:
                return {"level": level, "score": SALUTATION_MAP[level]}
    first_words = " ".join(tokenize_words(text)[:10])
    for p in SALUTATION_PHRASES["normal"]:
        if p in first_words:
            return {"level": "normal", "score": SALUTATION_MAP["normal"]}
    return {"level": "no salulation", "score": SALUTATION_MAP["no salulation"]}

MUST_HAVE_KEYS = {"name", "age", "school", "class", "family", "hobbies", "interest", "hobby"}
GOOD_TO_HAVE_KEYS = {"fun", "fun fact", "ambition", "goal", "dream", "strength", "achievement", "origin", "from", "about family"}

def count_must_good_keywords(text: str) -> Dict[str, int]:
    t = text.lower()
    words = set(tokenize_words(t))
    must = 0
    good = 0
    for k in MUST_HAVE_KEYS:
        if " " in k:
            if k in t:
                must += 1
        else:
            if k in words:
                must += 1
    for k in GOOD_TO_HAVE_KEYS:
        if " " in k:
            if k in t:
                good += 1
        else:
            if k in words:
                good += 1
    return {"must": must, "good": good}

def detect_flow(text: str) -> bool:
    t = text.lower()
    sal_idx = -1
    for p in SALUTATION_PHRASES["normal"] + SALUTATION_PHRASES["good"] + SALUTATION_PHRASES["excellent"]:
        idx = t.find(p)
        if idx >= 0:
            sal_idx = idx
            break
    name_patterns = ["my name is", "myself", "i am", "i'm", "this is"]
    name_idx = min([t.find(p) for p in name_patterns if t.find(p) >= 0] or [999999])
    if sal_idx >= 0 and name_idx >= 0 and (name_idx - sal_idx) < 200:
        return True
    if any(p in t for p in name_patterns):
        return True
    return False

# Speech rate scoring
def speech_rate_score(words: int, duration_sec: Optional[float]) -> float:
    if not duration_sec or duration_sec <= 0:
        duration_sec = max(1.0, words / 120.0 * 60.0)
    wpm = words / (duration_sec / 60.0)
    if wpm > 161:
        return 2.0
    if 141 <= wpm <= 160:
        return 6.0
    if 111 <= wpm <= 140:
        return 10.0
    if 81 <= wpm <= 110:
        return 6.0
    return 2.0

def grammar_score(text: str) -> float:
    wc = max(1, word_count(text))
    errors_per_100 = 0.0
    if _LT_TOOL:
        try:
            matches = _LT_TOOL.check(text)
            errors = len(matches)
            errors_per_100 = errors / (wc / 100.0)
        except Exception:
            errors_per_100 = 0.0
    else:
        errs = 0
        repeats = re.findall(r"\b(\w+)\s+\1\b", text.lower())
        errs += len(repeats)
        errs += max(0, text.count(",") - 5)
        errors_per_100 = errs / (wc / 100.0) if wc > 0 else 0.0
    gram_score = 1.0 - min(errors_per_100 / 10.0, 1.0)
    if gram_score > 0.9:
        return 10.0
    if 0.7 <= gram_score <= 0.89:
        return 8.0
    if 0.5 <= gram_score <= 0.69:
        return 6.0
    if 0.3 <= gram_score <= 0.49:
        return 4.0
    return 2.0

def ttr_score(text: str) -> float:
    words = tokenize_words(text)
    total = len(words)
    if total == 0:
        return 0.0
    distinct = len(set(words))
    ttr = distinct / total
    if 0.9 <= ttr <= 1.0:
        return 10.0
    if 0.7 <= ttr < 0.9:
        return 8.0
    if 0.5 <= ttr < 0.7:
        return 6.0
    if 0.3 <= ttr < 0.5:
        return 4.0
    return 2.0

FILLER_WORDS = {"um", "uh", "like", "you know", "so", "actually", "basically", "right", "i mean", "well", "kinda", "sort of", "okay", "hmm", "ah", "erm", "uhm"}
def filler_rate_score(text: str) -> float:
    words = tokenize_words(text)
    total = len(words)
    if total == 0:
        return 0.0
    t = text.lower()
    count = 0
    for fw in FILLER_WORDS:
        count += t.count(fw)
    rate = (count / total) * 100.0
    if rate <= 3.0:
        return 15.0
    if 4.0 <= rate <= 6.0:
        return 12.0
    if 7.0 <= rate <= 9.0:
        return 9.0
    if 10.0 <= rate <= 12.0:
        return 6.0
    return 3.0

def engagement_score(text: str) -> float:
    if _VADER:
        s = _VADER.polarity_scores(text)
        p = (s.get("compound", 0.0) + 1.0) / 2.0
    else:
        pos_words = {"good", "great", "excited", "happy", "enjoy", "love", "like", "confident", "interesting", "fun"}
        words = tokenize_words(text)
        if not words:
            p = 0.0
        else:
            p = sum(1 for w in words if w in pos_words) / len(words)
            p = min(1.0, p * 2.0)
    if p >= 0.9:
        return 15.0
    if 0.7 <= p <= 0.89:
        return 12.0
    if 0.5 <= p <= 0.69:
        return 9.0
    if 0.3 <= p <= 0.49:
        return 6.0
    return 3.0

# Criterion-level scorers
def score_content_structure(text: str) -> Dict[str, Any]:
    sal = detect_salutation(text)
    sal_pts = sal["score"]
    kw = count_must_good_keywords(text)
    must_pts = min(5, kw["must"]) * 4.0
    good_pts = min(5, kw["good"]) * 2.0
    flow_pts = 5.0 if detect_flow(text) else 0.0
    raw = sal_pts + must_pts + good_pts + flow_pts
    raw = max(0.0, min(40.0, raw))
    rule_0_100 = (raw / 40.0) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Salutation name age class school family hobbies flow closing")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Content & Structure", "raw_points": raw, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {"salutation": sal, "must": kw["must"], "good": kw["good"]}, "max_points": CRITERION_POINTS["Content & Structure"]}

def score_speech_rate(text: str, duration_sec: Optional[float]) -> Dict[str, Any]:
    words = word_count(text)
    pts = speech_rate_score(words, duration_sec)
    rule_0_100 = (pts / CRITERION_POINTS["Speech Rate"]) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Speech rate pacing")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Speech Rate", "raw_points": pts, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {"words": words, "duration_sec": duration_sec}, "max_points": CRITERION_POINTS["Speech Rate"]}

def score_language_grammar(text: str) -> Dict[str, Any]:
    gram_pts = grammar_score(text)
    rule_0_100 = (gram_pts / 10.0) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Grammar correctness")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Language & Grammar", "raw_points": gram_pts, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {}, "max_points": 10.0}

def score_vocabulary(text: str) -> Dict[str, Any]:
    ttr_pts = ttr_score(text)
    rule_0_100 = (ttr_pts / 10.0) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Vocabulary richness lexical diversity TTR")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Vocabulary Richness", "raw_points": ttr_pts, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {}, "max_points": CRITERION_POINTS["Vocabulary Richness"]}

def score_clarity(text: str) -> Dict[str, Any]:
    filler_pts = filler_rate_score(text)
    rule_0_100 = (filler_pts / CRITERION_POINTS["Clarity"]) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Clarity minimal fillers")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Clarity", "raw_points": filler_pts, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {}, "max_points": CRITERION_POINTS["Clarity"]}

def score_engagement(text: str) -> Dict[str, Any]:
    eng_pts = engagement_score(text)
    rule_0_100 = (eng_pts / CRITERION_POINTS["Engagement"]) * 100.0
    sem_0_100 = semantic_similarity_score(text, "Engagement enthusiasm sentiment positivity")
    combined = 0.5 * rule_0_100 + 0.5 * sem_0_100
    return {"criterion": "Engagement", "raw_points": eng_pts, "rule_score": rule_0_100, "semantic_score": sem_0_100, "combined_score": combined, "details": {}, "max_points": CRITERION_POINTS["Engagement"]}

def score_transcript(transcript: str, rubric: Optional[List[Dict[str, Any]]] = None, duration_sec: Optional[float] = None) -> Dict[str, Any]:
    cs = score_content_structure(transcript)
    sr = score_speech_rate(transcript, duration_sec)
    lg = score_language_grammar(transcript)
    vr = score_vocabulary(transcript)
    cl = score_clarity(transcript)
    en = score_engagement(transcript)

    # determine weight map
    if rubric:
        weight_map = {r["criterion"].lower(): float(r.get("weight", 0.0)) for r in rubric}
    else:
        total = sum(CRITERION_POINTS.values())
        weight_map = {k.lower(): CRITERION_POINTS[k] / total for k in CRITERION_POINTS}

    per_list = []

    def add_item(item, key_name):
        weight = weight_map.get(key_name.lower(), 0.0)
        weighted_contribution = (item["combined_score"] / 100.0) * (weight * 100.0)
        per_list.append({
            "criterion": item["criterion"],
            "weight": weight,
            "rule_score": item.get("rule_score"),
            "semantic_score": item.get("semantic_score"),
            "combined_score": item.get("combined_score"),
            "weighted_contribution": weighted_contribution,
            "raw_points": item.get("raw_points"),
            "details": item.get("details", {})
        })

    add_item(cs, "content & structure")
    add_item(sr, "speech rate")
    # combine language & vocabulary into one display item but keep calculations separate
    lg_vr_combined = 0.5 * lg["combined_score"] + 0.5 * vr["combined_score"]
    lg_vr_item = {
        "criterion": "Language & Grammar",
        "weight": weight_map.get("language & grammar", 0.0),
        "rule_score": 0.5 * lg["rule_score"] + 0.5 * vr["rule_score"],
        "semantic_score": 0.5 * lg["semantic_score"] + 0.5 * vr["semantic_score"],
        "combined_score": lg_vr_combined,
        "raw_points": lg.get("raw_points", 0) + vr.get("raw_points", 0),
        "details": {"grammar": lg.get("details", {}), "vocabulary": vr.get("details", {})}
    }
    add_item(lg_vr_item, "language & grammar")
    add_item(vr, "vocabulary richness")
    add_item(cl, "clarity")
    add_item(en, "engagement")

    overall = sum(p["weighted_contribution"] for p in per_list)
    overall = max(0.0, min(100.0, overall))

    return {"overall_score": overall, "per_criterion": per_list, "words": word_count(transcript)}
