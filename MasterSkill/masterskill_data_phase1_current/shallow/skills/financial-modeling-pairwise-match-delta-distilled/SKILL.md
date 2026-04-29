# Distilled Pairwise Match Delta

Computes odd-game Player 1 vs even-game Player 2 match delta from `/root/data.xlsx` using only the game index and one win-determining field confirmed from `/root/background.pdf`.

## When to Use

Use when the task asks for one numeric answer from `/root/data.xlsx` and `/root/background.pdf`, with adjacent odd/even games matched head-to-head and the required output is `/root/answer.txt`.

## How to Use

1. Extract text from `/root/background.pdf` with `pypdf.PdfReader` only. Stop as soon as you identify: the game-number column, the field that decides which game beats the other, and whether larger or smaller values win.
2. Inspect `/root/data.xlsx` with `pandas.ExcelFile` and read only sheet names plus a few top rows per candidate sheet. Pick the sheet containing game-level rows; ignore summary, pivot, and chart tabs.
3. Load only the needed columns. Normalize headers, coerce game numbers to integers and the comparison field to numeric, drop rows missing either value, sort by game number.
4. Pair games strictly as `(1,2)`, `(3,4)`, `(5,6)` by deriving a pair id from the game number. Odd games are Player 1, even games are Player 2. Ignore any unpaired trailing game.
5. Compare the paired values with a vectorized rule. Count a Player 1 win when the odd-game row wins the comparison, count a Player 2 win when the even-game row wins, and count ties as 0 unless the PDF explicitly says otherwise.
6. Compute `(Player 1 match wins) - (Player 2 match wins)` and write only that integer to `/root/answer.txt`.
7. Finalization checklist: reopen `/root/answer.txt`, strip whitespace, verify it matches `^-?\d+$`, ensure the file is non-empty and contains no label or extra text, then print the exact validated file content as the final line of execution.

## Scripts

### pairwise_delta.py

```
import argparse
import pandas as pd


def solve(xlsx_path, sheet_name, game_col, value_col, answer_path, lower_wins=False):
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, usecols=[game_col, value_col])
    df = df.rename(columns={game_col: 'game', value_col: 'value'})
    df['game'] = pd.to_numeric(df['game'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['game', 'value']).copy()
    df['game'] = df['game'].astype(int)
    df = df.sort_values('game')

    odd = df[df['game'] % 2 == 1][['game', 'value']].copy()
    even = df[df['game'] % 2 == 0][['game', 'value']].copy()
    odd['pair'] = (odd['game'] + 1) // 2
    even['pair'] = even['game'] // 2

    merged = odd[['pair', 'value']].merge(
        even[['pair', 'value']],
        on='pair',
        how='inner',
        suffixes=('_p1', '_p2')
    )

    if lower_wins:
        p1_wins = (merged['value_p1'] < merged['value_p2']).sum()
        p2_wins = (merged['value_p2'] < merged['value_p1']).sum()
    else:
        p1_wins = (merged['value_p1'] > merged['value_p2']).sum()
        p2_wins = (merged['value_p2'] > merged['value_p1']).sum()

    result = int(p1_wins - p2_wins)
    with open(answer_path, 'w', encoding='utf-8') as f:
        f.write(str(result))

    with open(answer_path, 'r', encoding='utf-8') as f:
        final_text = f.read().strip()
    if not final_text or not final_text.lstrip('-').isdigit():
        raise ValueError('answer.txt must contain only one integer')
    print(final_text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--xlsx', default='/root/data.xlsx')
    parser.add_argument('--sheet', required=True)
    parser.add_argument('--game-col', required=True)
    parser.add_argument('--value-col', required=True)
    parser.add_argument('--answer', default='/root/answer.txt')
    parser.add_argument('--lower-wins', action='store_true')
    args = parser.parse_args()
    solve(args.xlsx, args.sheet, args.game_col, args.value_col, args.answer, args.lower_wins)

```

