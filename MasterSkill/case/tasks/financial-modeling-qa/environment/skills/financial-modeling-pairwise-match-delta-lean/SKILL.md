# Lean Pairwise Match Delta

Compute Player 1 odd-game vs Player 2 even-game match delta from an Excel workbook after a minimal PDF lookup identifies the game column, comparison field, and win direction.

## When to Use

Use when a task asks for one numeric answer from `/root/data.xlsx` plus `/root/background.pdf`, where odd and even game numbers are paired head-to-head and the result must be written to `/root/answer.txt`.

## How to Use

1. Extract text from `/root/background.pdf` with `pypdf.PdfReader` and stop as soon as you identify three things: the game-number column, the field that determines which game wins, and whether higher or lower values win. Do not render pages or do broad PDF inspection unless text extraction fails.
2. Open `/root/data.xlsx` with `pandas.ExcelFile`, list sheet names, and sample only a few header rows from likely game-level sheets. Skip summary, pivot, chart, and notes tabs.
3. Load only the needed columns from the chosen sheet. Normalize headers, coerce the game column to integer and the comparison field to numeric, drop blank or summary rows, sort by game number, and ignore any unmatched final odd game.
4. Pair `(1,2)`, `(3,4)`, `(5,6)`, ... where odd games are Player 1 and even games are Player 2. If the workbook has a background-defined winner/result column, use it directly; otherwise compare the identified metric using the PDF-defined win direction. Treat ties as 0 unless the background gives a tiebreak rule.
5. Compute `(number of Player 1 match wins) - (number of Player 2 match wins)` with a vectorized merge on pair id.
6. Write only the integer answer to `/root/answer.txt` with no label or explanation.
7. Finalization checklist: reopen `/root/answer.txt`; verify it matches `^-?\\d+$`; sanity-check the first few pairs against the source rows; then print the exact validated file content before exit.

## Scripts

### pairwise_delta_from_columns.py

```
import argparse\nimport re\nimport pandas as pd\n\n\ndef main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument('--xlsx', required=True)\n    ap.add_argument('--sheet', required=True)\n    ap.add_argument('--game-col', required=True)\n    ap.add_argument('--value-col', required=True)\n    ap.add_argument('--answer', default='/root/answer.txt')\n    ap.add_argument('--lower-wins', action='store_true')\n    args = ap.parse_args()\n\n    df = pd.read_excel(args.xlsx, sheet_name=args.sheet, usecols=[args.game_col, args.value_col])\n    df = df.rename(columns={args.game_col: 'game', args.value_col: 'value'})\n    df['game'] = pd.to_numeric(df['game'], errors='coerce')\n    df['value'] = pd.to_numeric(df['value'], errors='coerce')\n    df = df.dropna(subset=['game', 'value']).copy()\n    df['game'] = df['game'].astype(int)\n    df = df.sort_values('game').drop_duplicates('game', keep='first')\n\n    odd = df[df['game'] % 2 == 1][['game', 'value']].copy()\n    even = df[df['game'] % 2 == 0][['game', 'value']].copy()\n    odd['pair'] = (odd['game'] + 1) // 2\n    even['pair'] = even['game'] // 2\n\n    merged = odd.merge(even, on='pair', how='inner', suffixes=('_p1', '_p2'))\n\n    if args.lower_wins:\n        p1_wins = (merged['value_p1'] < merged['value_p2']).sum()\n        p2_wins = (merged['value_p2'] < merged['value_p1']).sum()\n    else:\n        p1_wins = (merged['value_p1'] > merged['value_p2']).sum()\n        p2_wins = (merged['value_p2'] > merged['value_p1']).sum()\n\n    result = int(p1_wins - p2_wins)\n    with open(args.answer, 'w', encoding='utf-8') as f:\n        f.write(str(result))\n\n    with open(args.answer, 'r', encoding='utf-8') as f:\n        text = f.read().strip()\n    if not re.fullmatch(r'-?\\d+', text):\n        raise SystemExit(f'invalid answer format: {text!r}')\n    print(text)\n\n\nif __name__ == '__main__':\n    main()\n
```

