#!/usr/bin/env python3
"""Deterministic taxonomy pipeline for taxonomy-tree-merge.

This script is intentionally executable end-to-end inside the task container so the
agent can follow a short, reliable workflow instead of inventing clustering code
from scratch during the benchmark run.
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer


MAX_LEVELS = 5
TOP_LEVEL_CLUSTERS = 12
MAX_CHILDREN = 12
MIN_CLUSTER_SIZE = 24
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
    "supplies",
    "supply",
    "product",
    "products",
    "equipment",
    "part",
    "parts",
    "set",
    "kit",
}
SPECIAL_PATTERN = re.compile(r"[^a-z0-9| >]+")


@dataclass
class ClusterNode:
    level: int
    name: str
    indices: np.ndarray
    ancestor_tokens: set[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unified taxonomy outputs for taxonomy-tree-merge.")
    parser.add_argument("--amazon", required=True)
    parser.add_argument("--facebook", required=True)
    parser.add_argument("--google", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def normalize_token(token: str) -> str:
    token = SPECIAL_PATTERN.sub(" ", token.lower())
    token = re.sub(r"\s+", " ", token).strip()
    if not token:
        return ""
    words: list[str] = []
    for word in token.split():
        word = singularize_word(word)
        words.append(word)
    return " ".join(words).strip()


def singularize_word(word: str) -> str:
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


def normalize_segment(segment: str) -> str:
    segment = segment.replace("&", " and ")
    segment = segment.replace("/", " ")
    segment = segment.replace("-", " ")
    segment = segment.replace("'", " ")
    segment = segment.replace(",", " ")
    segment = re.sub(r"\s+", " ", segment).strip()
    return normalize_token(segment)


def normalize_path(path: str) -> list[str]:
    raw_segments = [part.strip() for part in str(path).split(">")]
    segments = [normalize_segment(part) for part in raw_segments]
    segments = [segment for segment in segments if segment]
    if len(segments) > MAX_LEVELS:
        segments = segments[:MAX_LEVELS]
    return segments


def load_source(path: str, source_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "category_path" not in df.columns:
        raise ValueError(f"missing category_path column in {path}")
    out = pd.DataFrame(
        {
            "source": source_name,
            "raw_category_path": df["category_path"].astype(str),
        }
    )
    out["segments"] = out["raw_category_path"].map(normalize_path)
    out = out[out["segments"].map(bool)].copy()
    out["category_path"] = out["segments"].map(lambda parts: " > ".join(parts))
    out["depth"] = out["segments"].map(len)
    return out


def remove_prefix_paths(df: pd.DataFrame) -> pd.DataFrame:
    paths = sorted(df["category_path"].unique(), key=lambda text: (text.count(">"), len(text)))
    path_set = set(paths)
    blocked: set[str] = set()
    for path in paths:
        if path in blocked:
            continue
        parts = path.split(" > ")
        for size in range(1, len(parts)):
            blocked.add(" > ".join(parts[:size]))
    kept = df[~df["category_path"].isin(blocked)].copy()
    kept = kept.drop_duplicates(subset=["source", "category_path"]).reset_index(drop=True)
    return kept


def tokens_for_text(text: str) -> list[str]:
    return [tok for tok in text.split() if tok and tok not in STOPWORDS]


def choose_cluster_count(size: int, top_level: bool = False) -> int:
    if top_level:
        return max(10, min(TOP_LEVEL_CLUSTERS, size))
    if size < MIN_CLUSTER_SIZE * 2:
        return 1
    estimate = int(round(math.sqrt(size) / 2.2))
    return max(3, min(MAX_CHILDREN, estimate))


def build_labels(texts: list[str], clusters: int) -> np.ndarray:
    if not texts:
        return np.array([], dtype=int)
    unique_texts = len(set(texts))
    clusters = max(1, min(clusters, unique_texts, len(texts)))
    if clusters == 1:
        return np.zeros(len(texts), dtype=int)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.95)
    matrix = vectorizer.fit_transform(texts)
    model = MiniBatchKMeans(
        n_clusters=clusters,
        random_state=0,
        batch_size=min(2048, len(texts)),
        n_init=10,
    )
    return model.fit_predict(matrix)


def candidate_tokens(records: pd.DataFrame, ancestor_tokens: set[str]) -> list[tuple[str, float, int]]:
    counts = Counter()
    coverage = Counter()
    for _, row in records.iterrows():
        tokens = set()
        for segment in row["segments"]:
            for token in tokens_for_text(segment):
                if token not in ancestor_tokens:
                    counts[token] += 1
                    tokens.add(token)
        for token in tokens:
            coverage[token] += 1
    scored = []
    total = max(len(records), 1)
    for token, freq in counts.items():
        cov = coverage[token] / total
        if cov < 0.12:
            continue
        scored.append((token, cov, freq))
    scored.sort(key=lambda item: (item[1], item[2], item[0]), reverse=True)
    return scored


def build_cluster_name(records: pd.DataFrame, ancestor_tokens: set[str], sibling_names: list[set[str]]) -> str:
    scored = candidate_tokens(records, ancestor_tokens)
    selected: list[str] = []
    selected_sets = [set(name) for name in sibling_names]

    def coverage_for(tokens: list[str]) -> float:
        if not tokens:
            return 0.0
        matched = 0
        token_set = set(tokens)
        for segments in records["segments"]:
            path_tokens = {tok for segment in segments for tok in tokens_for_text(segment)}
            if token_set & path_tokens:
                matched += 1
        return matched / max(len(records), 1)

    for token, _, _ in scored:
        if token in selected:
            continue
        trial = selected + [token]
        trial_set = set(trial)
        too_close = False
        for sibling in selected_sets:
            overlap = len(trial_set & sibling) / max(len(trial_set), len(sibling), 1)
            if overlap > 0.30:
                too_close = True
                break
        if too_close and selected:
            continue
        selected.append(token)
        if coverage_for(selected) >= 0.72 or len(selected) >= 3:
            break

    if not selected:
        selected = ["catalog"]

    return " | ".join(selected[:5])


def assign_level_names(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for level in range(1, MAX_LEVELS + 1):
        result[f"unified_level_{level}"] = pd.NA

    root_texts = result["segments"].map(lambda segs: " ".join(segs)).tolist()
    root_labels = build_labels(root_texts, choose_cluster_count(len(result), top_level=True))

    frontier: list[ClusterNode] = []
    sibling_tokens: list[set[str]] = []
    for cluster_id in sorted(set(root_labels.tolist())):
        indices = np.where(root_labels == cluster_id)[0]
        cluster_df = result.iloc[indices]
        name = build_cluster_name(cluster_df, set(), sibling_tokens)
        name_tokens = set(name.replace("|", " ").split())
        sibling_tokens.append(name_tokens)
        result.iloc[indices, result.columns.get_loc("unified_level_1")] = name
        frontier.append(ClusterNode(level=1, name=name, indices=indices, ancestor_tokens=name_tokens))

    while frontier:
        node = frontier.pop(0)
        if node.level >= MAX_LEVELS:
            continue
        cluster_df = result.iloc[node.indices]
        remaining_texts: list[str] = []
        viable_indices: list[int] = []
        for idx, segments in zip(node.indices, cluster_df["segments"]):
            suffix_parts = []
            for segment in segments:
                filtered = [tok for tok in tokens_for_text(segment) if tok not in node.ancestor_tokens]
                if filtered:
                    suffix_parts.append(" ".join(filtered))
            text = " ".join(suffix_parts).strip()
            if text:
                viable_indices.append(idx)
                remaining_texts.append(text)
        if len(viable_indices) < MIN_CLUSTER_SIZE:
            continue

        child_clusters = choose_cluster_count(len(viable_indices))
        if child_clusters <= 1:
            continue

        child_labels = build_labels(remaining_texts, child_clusters)
        sibling_names: list[set[str]] = []
        next_level = node.level + 1

        for child_id in sorted(set(child_labels.tolist())):
            child_indices = np.array([viable_indices[i] for i, label in enumerate(child_labels) if label == child_id])
            child_df = result.iloc[child_indices]
            name = build_cluster_name(child_df, node.ancestor_tokens, sibling_names)
            name_tokens = set(name.replace("|", " ").split())
            sibling_names.append(name_tokens)
            result.iloc[child_indices, result.columns.get_loc(f"unified_level_{next_level}")] = name
            frontier.append(
                ClusterNode(
                    level=next_level,
                    name=name,
                    indices=child_indices,
                    ancestor_tokens=node.ancestor_tokens | name_tokens,
                )
            )

    return result


def propagate_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for idx, row in out.iterrows():
        seen_tokens: set[str] = set()
        for level in range(1, MAX_LEVELS + 1):
            col = f"unified_level_{level}"
            value = row[col]
            if pd.isna(value):
                continue
            tokens = [tok for tok in str(value).replace("|", " ").split() if tok not in seen_tokens]
            if not tokens:
                out.at[idx, col] = pd.NA
                continue
            out.at[idx, col] = " | ".join(tokens[:5])
            seen_tokens.update(tokens)
        for level in range(2, MAX_LEVELS + 1):
            prev_col = f"unified_level_{level - 1}"
            col = f"unified_level_{level}"
            if pd.notna(out.at[idx, col]) and pd.isna(out.at[idx, prev_col]):
                out.at[idx, col] = pd.NA
    return out


def finalize_outputs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    level_cols = [f"unified_level_{level}" for level in range(1, MAX_LEVELS + 1)]
    full = df[["source", "category_path", "depth", *level_cols]].copy()
    hierarchy = full[level_cols].dropna(subset=["unified_level_1"]).drop_duplicates().reset_index(drop=True)
    return full, hierarchy


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = [
        load_source(args.amazon, "amazon"),
        load_source(args.facebook, "facebook"),
        load_source(args.google, "google"),
    ]
    merged = pd.concat(frames, ignore_index=True)
    merged = remove_prefix_paths(merged)
    clustered = assign_level_names(merged)
    clustered = propagate_hierarchy(clustered)
    full, hierarchy = finalize_outputs(clustered)

    full.to_csv(output_dir / "unified_taxonomy_full.csv", index=False)
    hierarchy.to_csv(output_dir / "unified_taxonomy_hierarchy.csv", index=False)
    print(f"wrote {len(full)} rows to {output_dir / 'unified_taxonomy_full.csv'}")
    print(f"wrote {len(hierarchy)} rows to {output_dir / 'unified_taxonomy_hierarchy.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
