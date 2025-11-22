from pathlib import Path
import pandas as pd

def _normalize_weight_map(df: pd.DataFrame):
    # expects columns: 'Criteria' and 'Weight' or similar; fallback to uniform weights
    if "Criteria" in df.columns and "Weight" in df.columns:
        items = []
        total = df["Weight"].sum()
        for _, r in df.iterrows():
            items.append({"criterion": r["Criteria"], "weight": float(r["Weight"]), "keywords": []})
        if total > 0:
            for it in items:
                it["weight"] = it["weight"] / total
        return items
    # fallback: attempt to parse first column as criterion names
    crits = [c for c in df.iloc[:,0].dropna().astype(str).tolist() if c.strip()]
    if crits:
        w = 1.0 / len(crits)
        return [{"criterion": c, "weight": w, "keywords": []} for c in crits]
    return []

def load_rubric(path: str | Path | None = None):
    # Try provided path, otherwise search common files in project root
    p = Path(path) if path else None
    candidates = []
    if p and p.exists():
        candidates.append(p)
    else:
        for name in ("Case study for interns.xlsx", "Rubrik.csv", "rubric_clean.csv"):
            fp = Path(name)
            if fp.exists():
                candidates.append(fp)
    if not candidates:
        raise FileNotFoundError("No rubric file found in project root.")
    f = candidates[0]
    if f.suffix.lower() in (".xls", ".xlsx"):
        df = pd.read_excel(f, header=0, dtype=str)
    else:
        df = pd.read_csv(f, header=0, dtype=str, keep_default_na=False)
    # Clean dataframe: unify column names
    df.columns = [str(c).strip() for c in df.columns]
    # If file is the human-friendly template, try to extract Criteria and Weight columns
    # Attempt common patterns
    col_map = {c.lower(): c for c in df.columns}
    if any(k in col_map for k in ("criteria", "creteria", "criterion")):
        crit_col = col_map.get("criteria") or col_map.get("creteria") or col_map.get("criterion")
    else:
        crit_col = df.columns[0]
    weight_col = None
    for guess in ("weight", "weightage", "weight (%)", "weight (%) "):
        if guess in col_map:
            weight_col = col_map[guess]
            break
    if weight_col:
        try:
            df2 = df[[crit_col, weight_col]].copy()
            df2.columns = ["Criteria", "Weight"]
            df2["Weight"] = pd.to_numeric(df2["Weight"], errors="coerce").fillna(0.0)
            items = _normalize_weight_map(df2)
            return items
        except Exception:
            pass
    # fallback: list unique non-empty entries in first col
    items = _normalize_weight_map(df)
    if not items:
        # final generic fallback
        return [{"criterion": "Content & Structure", "weight": 0.36, "keywords": []},
                {"criterion": "Speech Rate", "weight": 0.09, "keywords": []},
                {"criterion": "Language & Grammar", "weight": 0.18, "keywords": []},
                {"criterion": "Vocabulary Richness", "weight": 0.09, "keywords": []},
                {"criterion": "Clarity", "weight": 0.14, "keywords": []},
                {"criterion": "Engagement", "weight": 0.14, "keywords": []}]
    return items
