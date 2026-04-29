import re
import argparse
from typing import Optional, Tuple, Dict, List

import pandas as pd
from pypdf import PdfReader


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def extract_pdf_hints(pdf_path: str, char_budget: int = 30000, page_cap: int = 50) -> str:
    """Return a small text slice (not full PDF) to keep cost low."""
    reader = PdfReader(pdf_path)
    out = []
    total = 0
    for i, page in enumerate(reader.pages[: min(len(reader.pages), page_cap)]):
        txt = page.extract_text() or ""
        txt = _clean(txt)
        if not txt:
            continue
        out.append(txt)
        total += len(txt)
        if total >= char_budget:
            break
    return "\n".join(out)


def guess_win_direction(pdf_text: str) -> str:
    t = pdf_text.lower()
    # Heuristic: prefer explicit direction if present
    if re.search(r"\b(lower|smallest|minimum)\b.*\b(wins?|winner)\b|\b(wins?|winner)\b.*\b(lower|smallest|minimum)\b", t):
        return "lower"
    return "higher"  # default


def pick_sheet_and_columns(xlsx_path: str, pdf_text: str, explicit_sheet: Optional[str], explicit_game_col: Optional[str], explicit_value_col: Optional[str]) -> Tuple[str, str, str]:
    xl = pd.ExcelFile(xlsx_path)
    sheets = xl.sheet_names

    # If user specified everything, honor it.
    if explicit_sheet and explicit_game_col and explicit_value_col:
        return explicit_sheet, explicit_game_col, explicit_value_col

    # Build weak hints from PDF.
    pdf_l = pdf_text.lower()
    game_hints = ["game", "game #", "game no", "game number", "match", "index", "id"]
    metric_hints = []
    for k in ["score", "points", "value", "metric", "return", "profit", "pnl", "revenue", "wins", "result", "total", "amount"]:
        if k in pdf_l:
            metric_hints.append(k)

    def score_cols(cols: List[str]) -> Tuple[int, int, Optional[str], Optional[str]]:
        cols_l = [c.lower() for c in cols]
        game_col = None
        value_col = None
        gscore = 0
        vscore = 0

        # If explicit single col provided, prioritize it.
        if explicit_game_col and explicit_game_col in cols:
            game_col = explicit_game_col
            gscore += 100
        if explicit_value_col and explicit_value_col in cols:
            value_col = explicit_value_col
            vscore += 100

        # Otherwise heuristics.
        if not game_col:
            for c in cols:
                cl = c.lower()
                if any(h in cl for h in ["game", "match"]) or cl in ["g", "game#", "game_no", "gameid", "game_id", "game number"]:
                    game_col = c
                    gscore += 10
                    break
            if not game_col:
                for c in cols:
                    cl = c.lower()
                    if any(h in cl for h in ["index", "id", "no", "number", "#"]):
                        game_col = c
                        gscore += 3
                        break

        if not value_col:
            for c in cols:
                cl = c.lower()
                if any(h in cl for h in metric_hints):
                    value_col = c
                    vscore += 10
                    break
            if not value_col:
                # fallback: any numeric-ish column name
                for c in cols:
                    cl = c.lower()
                    if any(h in cl for h in ["score", "points", "total", "value", "amount", "profit", "return", "revenue", "result"]):
                        value_col = c
                        vscore += 5
                        break

        return gscore, vscore, game_col, value_col

    best = None  # (sheet_score, gscore, vscore, sheet, game_col, value_col)
    for sheet in sheets:
        cols = list(pd.read_excel(xlsx_path, sheet_name=sheet, nrows=0).columns)
        cols = [str(c) for c in cols]
        gscore, vscore, gcol, vcol = score_cols(cols)
        sheet_score = gscore + vscore
        # Avoid obvious summary sheets
        name_l = sheet.lower()
        if any(bad in name_l for bad in ["pivot", "summary", "chart", "dashboard"]):
            sheet_score -= 5
        candidate = (sheet_score, gscore, vscore, sheet, gcol, vcol)
        if best is None or candidate > best:
            best = candidate

    if best is None or best[0] <= 0 or not best[4] or not best[5]:
        raise RuntimeError("Could not confidently identify sheet/columns; pass --sheet/--game-col/--value-col explicitly.")

    return best[3], best[4], best[5]


def compute_delta(xlsx_path: str, sheet: str, game_col: str, value_col: str, win_direction: str) -> int:
    df = pd.read_excel(xlsx_path, sheet_name=sheet, usecols=[game_col, value_col])
    df = df.rename(columns={game_col: "game", value_col: "value"})
    df["game"] = pd.to_numeric(df["game"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["game", "value"]).copy()
    df["game"] = df["game"].astype(int)
    df = df.sort_values("game")

    odd = df[df["game"] % 2 == 1].copy()
    even = df[df["game"] % 2 == 0].copy()
    odd["pair"] = (odd["game"] + 1) // 2
    even["pair"] = even["game"] // 2

    merged = odd[["pair", "value"]].merge(
        even[["pair", "value"]], on="pair", how="inner", suffixes=("_p1", "_p2")
    )

    if win_direction == "lower":
        p1_wins = (merged["value_p1"] < merged["value_p2"]).sum()
        p2_wins = (merged["value_p2"] < merged["value_p1"]).sum()
    else:
        p1_wins = (merged["value_p1"] > merged["value_p2"]).sum()
        p2_wins = (merged["value_p2"] > merged["value_p1"]).sum()

    return int(p1_wins - p2_wins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="/root/data.xlsx")
    ap.add_argument("--pdf", default="/root/background.pdf")
    ap.add_argument("--answer", default="/root/answer.txt")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--game-col", default=None)
    ap.add_argument("--value-col", default=None)
    args = ap.parse_args()

    pdf_text = extract_pdf_hints(args.pdf)
    win_dir = guess_win_direction(pdf_text)

    sheet, game_col, value_col = pick_sheet_and_columns(
        args.xlsx, pdf_text, args.sheet, args.game_col, args.value_col
    )
    result = compute_delta(args.xlsx, sheet, game_col, value_col, win_dir)

    with open(args.answer, "w", encoding="utf-8") as f:
        f.write(str(result))

    # Minimal verifier-friendly echo
    with open(args.answer, "r", encoding="utf-8") as f:
        _ = int(f.read().strip())


if __name__ == "__main__":
    main()
