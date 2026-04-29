# Taxonomy Tree Merge (Fast, Deterministic)

Unifies multiple e-commerce category-path CSVs into a single 5-level taxonomy and outputs (1) full source-to-unified mapping and (2) the deduped unified hierarchy, using lightweight TF‑IDF + deterministic MiniBatchKMeans (no external embedding downloads).

## When to Use

Use when the task provides one or more CSVs with a `category_path` column containing hierarchical paths like `A > B > C`, and requires a unified 5-level taxonomy plus two CSV outputs (full mapping + hierarchy).

## How to Use

Run the end-to-end script (no extra steps):

1) Execute:
   python3 scripts/pipeline.py \
     --amazon /root/data/amazon_product_categories.csv \
     --facebook /root/data/fb_product_categories.csv \
     --google /root/data/google_shopping_product_categories.csv \
     --output-dir /root/output

2) Outputs written (verifier-facing artifacts):
   - /root/output/unified_taxonomy_full.csv
   - /root/output/unified_taxonomy_hierarchy.csv

3) Finalization checklist (must do before exiting):
   - Re-open both CSVs and parse with pandas.
   - Assert required columns exist:
     full: source, category_path, depth, unified_level_1..unified_level_5
     hierarchy: unified_level_1..unified_level_5
   - Assert `unified_level_1` is non-null for the vast majority of rows.
   - Assert hierarchy is deduped (drop_duplicates equals itself) and not empty.
   - Print a one-line summary: row counts for both files and top-level unique category count.

## Scripts

### scripts/pipeline.py

```
#!/usr/bin/env python3
"""Fast, deterministic taxonomy merge for taxonomy-tree-merge.

Reads 3 source CSVs (must have `category_path`), normalizes paths, keeps leaf paths,
then builds a unified 5-level taxonomy via recursive TF-IDF + MiniBatchKMeans.

Outputs:
- unified_taxonomy_full.csv: per-row mapping
- unified_taxonomy_hierarchy.csv: deduped unified paths
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer


MAX_LEVELS = 5
TOP_LEVEL_MIN = 10
TOP_LEVEL_MAX = 20
CHILD_MIN = 3
CHILD_MAX = 20
MIN_SPLIT_SIZE = 30
RANDOM_STATE = 0

STOPWORDS = {
    "and",
    "for",
    "the",
    "with",
    "other",
    "misc",
    "general",
    "accessory",
    "accessories",
    "supply",
    "supplies",
    "product",
    "products",
    "equipment",
    "part",
    "parts",
    "set",
    "kit",
}

NON_ALNUM = re.compile(r"[^a-z0-9 ]+")


@dataclass
class Node:
    level: int
    indices: np.ndarray
    ancestor_tokens: set[str]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--amazon", required=True)
    p.add_argument("--facebook", required=True)
    p.add_argument("--google", required=True)
    p.add_argument("--output-dir", required=True)
    return p.parse_args()


def singularize(word: str) -> str:
    irregular = {
        "women": "woman",
        "men": "man",
        "children": "child",
        "people": "person",
        "teeth": "tooth",
        "feet": "foot",
    }
    if word in irregular:
        return irregular[word]
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "xes", "zes")) and len(word) > 5:
        return word[:-2]
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]
    if word.endswith("ses") and not word.endswith("sses") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def normalize_segment(seg: str) -> str:
    seg = str(seg).lower()
    seg = seg.replace("&", " and ")
    seg = seg.replace("/", " ")
    seg = seg.replace("-", " ")
    seg = seg.replace("'", " ")
    seg = seg.replace(",", " ")
    seg = re.sub(r"\s+", " ", seg).strip()
    seg = NON_ALNUM.sub(" ", seg)
    seg = re.sub(r"\s+", " ", seg).strip()
    if not seg:
        return ""
    words = [singularize(w) for w in seg.split() if w]
    return " ".join(words).strip()


def normalize_path(path: str) -> list[str]:
    parts = [p.strip() for p in str(path).split(">")]
    segs = [normalize_segment(p) for p in parts]
    segs = [s for s in segs if s]
    return segs[:MAX_LEVELS]


def load_source(csv_path: str, source: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "category_path" not in df.columns:
        raise ValueError(f"missing category_path column in {csv_path}")

    out = pd.DataFrame(
        {
            "source": source,
            "raw_category_path": df["category_path"].astype(str),
        }
    )
    out["segments"] = out["raw_category_path"].map(normalize_path)
    out = out[out["segments"].map(bool)].copy()
    out["category_path"] = out["segments"].map(lambda s: " > ".join(s))
    out = out.drop_duplicates(subset=["source", "category_path"]).reset_index(drop=True)
    out["depth"] = out["segments"].map(len)
    return out


def remove_prefix_paths(df: pd.DataFrame) -> pd.DataFrame:
    # Keep only leaf paths (paths that are not a prefix of any longer path).
    paths = sorted(df["category_path"].unique(), key=lambda t: (t.count(">"), len(t)))
    blocked: set[str] = set()
    for p in paths:
        if p in blocked:
            continue
        parts = p.split(" > ")
        for k in range(1, len(parts)):
            blocked.add(" > ".join(parts[:k]))
    return df[~df["category_path"].isin(blocked)].copy().reset_index(drop=True)


def tokens(text: str) -> list[str]:
    return [t for t in text.split() if t and t not in STOPWORDS]


def choose_k(n: int, *, top: bool) -> int:
    if n <= 1:
        return 1
    if top:
        # Aim for 10–20 broad categories.
        return max(TOP_LEVEL_MIN, min(TOP_LEVEL_MAX, int(round(math.sqrt(n) * 1.2))))
    # Aim for 3–20 children per parent, scaled by cluster size.
    k = int(round(math.sqrt(n) / 2.0))
    return max(CHILD_MIN, min(CHILD_MAX, k))


def kmeans_labels(texts: list[str], k: int) -> np.ndarray:
    if not texts:
        return np.array([], dtype=int)
    uniq = len(set(texts))
    k = max(1, min(k, uniq, len(texts)))
    if k == 1:
        return np.zeros(len(texts), dtype=int)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.95)
    X = vec.fit_transform(texts)
    model = MiniBatchKMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        n_init=10,
        batch_size=min(2048, len(texts)),
    )
    return model.fit_predict(X)


def candidate_tokens(records: pd.DataFrame, ancestor: set[str]) -> list[tuple[str, float, int]]:
    counts = Counter()
    coverage = Counter()
    for _, row in records.iterrows():
        seen = set()
        for seg in row["segments"]:
            for tok in tokens(seg):
                if tok in ancestor:
                    continue
                counts[tok] += 1
                seen.add(tok)
        for tok in seen:
            coverage[tok] += 1

    total = max(len(records), 1)
    scored: list[tuple[str, float, int]] = []
    for tok, freq in counts.items():
        cov = coverage[tok] / total
        if cov < 0.12:
            continue
        scored.append((tok, cov, freq))
    scored.sort(key=lambda x: (x[1], x[2], x[0]), reverse=True)
    return scored


def build_name(records: pd.DataFrame, ancestor: set[str], sibling_token_sets: list[set[str]]) -> str:
    scored = candidate_tokens(records, ancestor)

    def cov(selected: list[str]) -> float:
        if not selected:
            return 0.0
        sel = set(selected)
        hit = 0
        for segs in records["segments"]:
            path_toks = {t for s in segs for t in tokens(s)}
            if sel & path_toks:
                hit += 1
        return hit / max(len(records), 1)

    selected: list[str] = []
    for tok, _, _ in scored:
        if tok in selected:
            continue
        trial = selected + [tok]
        tset = set(trial)
        # Enforce sibling distinctness (< ~30% overlap).
        too_close = False
        for sib in sibling_token_sets:
            overlap = len(tset & sib) / max(len(tset), len(sib), 1)
            if overlap > 0.30:
                too_close = True
                break
        if too_close and selected:
            continue
        selected.append(tok)
        if cov(selected) >= 0.72 or len(selected) >= 3:
            break

    if not selected:
        selected = ["catalog"]
    return " | ".join(selected[:5])


def assign_taxonomy(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for lvl in range(1, MAX_LEVELS + 1):
        out[f"unified_level_{lvl}"] = pd.NA

    root_texts = out["segments"].map(lambda s: " ".join(s)).tolist()
    root_labels = kmeans_labels(root_texts, choose_k(len(out), top=True))

    frontier: list[Node] = []
    root_siblings: list[set[str]] = []

    for cid in sorted(set(root_labels.tolist())):
        idxs = np.where(root_labels == cid)[0]
        recs = out.iloc[idxs]
        name = build_name(recs, set(), root_siblings)
        name_tokens = set(name.replace("|", " ").split())
        root_siblings.append(name_tokens)
        out.iloc[idxs, out.columns.get_loc("unified_level_1")] = name
        frontier.append(Node(level=1, indices=idxs, ancestor_tokens=name_tokens))

    # BFS-style expansion.
    while frontier:
        node = frontier.pop(0)
        if node.level >= MAX_LEVELS:
            continue
        recs = out.iloc[node.indices]

        viable: list[int] = []
        suffix_texts: list[str] = []
        for idx, segs in zip(node.indices, recs["segments"]):
            suffix_parts: list[str] = []
            for seg in segs:
                kept = [t for t in tokens(seg) if t not in node.ancestor_tokens]
                if kept:
                    suffix_parts.append(" ".join(kept))
            txt = " ".join(suffix_parts).strip()
            if txt:
                viable.append(int(idx))
                suffix_texts.append(txt)

        if len(viable) < MIN_SPLIT_SIZE:
            continue

        k = choose_k(len(viable), top=False)
        if k <= 1:
            continue

        labels = kmeans_labels(suffix_texts, k)
        next_level = node.level + 1
        siblings: list[set[str]] = []

        for cid in sorted(set(labels.tolist())):
            child_idxs = np.array([viable[i] for i, lab in enumerate(labels) if lab == cid], dtype=int)
            child_recs = out.iloc[child_idxs]
            name = build_name(child_recs, node.ancestor_tokens, siblings)
            name_tokens = set(name.replace("|", " ").split())
            siblings.append(name_tokens)
            out.iloc[child_idxs, out.columns.get_loc(f"unified_level_{next_level}")] = name
            frontier.append(
                Node(
                    level=next_level,
                    indices=child_idxs,
                    ancestor_tokens=node.ancestor_tokens | name_tokens,
                )
            )

    # Enforce no child without parent; and avoid repeating parent tokens in child.
    for i, row in out.iterrows():
        seen: set[str] = set()
        for lvl in range(1, MAX_LEVELS + 1):
            col = f"unified_level_{lvl}"
            val = row[col]
            if pd.isna(val):
                continue
            toks = [t for t in str(val).replace("|", " ").split() if t and t not in seen]
            if not toks:
                out.at[i, col] = pd.NA
                continue
            out.at[i, col] = " | ".join(toks[:5])
            seen |= set(toks)
        for lvl in range(2, MAX_LEVELS + 1):
            if pd.notna(out.at[i, f"unified_level_{lvl}"]) and pd.isna(out.at[i, f"unified_level_{lvl-1}"]):
                out.at[i, f"unified_level_{lvl}"] = pd.NA

    return out


def finalize_outputs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    level_cols = [f"unified_level_{i}" for i in range(1, MAX_LEVELS + 1)]
    full = df[["source", "category_path", "depth", *level_cols]].copy()
    hierarchy = full[level_cols].dropna(subset=["unified_level_1"]).drop_duplicates().reset_index(drop=True)
    return full, hierarchy


def main() -> int:
    args = parse_args()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    frames = [
        load_source(args.amazon, "amazon"),
        load_source(args.facebook, "facebook"),
        load_source(args.google, "google"),
    ]
    merged = pd.concat(frames, ignore_index=True)
    merged = remove_prefix_paths(merged)

    clustered = assign_taxonomy(merged)
    full, hierarchy = finalize_outputs(clustered)

    full_path = outdir / "unified_taxonomy_full.csv"
    hier_path = outdir / "unified_taxonomy_hierarchy.csv"
    full.to_csv(full_path, index=False)
    hierarchy.to_csv(hier_path, index=False)

    # Finalization: re-open and sanity-check.
    full2 = pd.read_csv(full_path)
    hier2 = pd.read_csv(hier_path)

    required_full = {"source", "category_path", "depth"} | {f"unified_level_{i}" for i in range(1, MAX_LEVELS + 1)}
    required_hier = {f"unified_level_{i}" for i in range(1, MAX_LEVELS + 1)}
    if not required_full.issubset(set(full2.columns)):
        raise ValueError(f"full CSV missing columns: {sorted(required_full - set(full2.columns))}")
    if not required_hier.issubset(set(hier2.columns)):
        raise ValueError(f"hierarchy CSV missing columns: {sorted(required_hier - set(hier2.columns))}")
    if len(hier2) == 0:
        raise ValueError("hierarchy CSV is empty")

    top_n = hier2["unified_level_1"].nunique(dropna=True)
    mapped = full2["unified_level_1"].notna().mean() if len(full2) else 0.0

    print(f"wrote {len(full2)} rows to {full_path}")
    print(f"wrote {len(hier2)} rows to {hier_path}")
    print(f"top_level_unique={top_n} mapped_ratio={mapped:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

