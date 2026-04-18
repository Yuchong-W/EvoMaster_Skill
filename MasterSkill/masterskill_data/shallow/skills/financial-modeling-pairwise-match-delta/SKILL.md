# Pairwise Match Delta from Excel

Solve workbook-based game questions by identifying the game index and winner metric from the background PDF, pairing odd and even games, and computing Player 1 wins minus Player 2 wins with a direct vectorized calculation.

## When to Use

Use when a task asks for a single numeric answer from `/root/data.xlsx` and `/root/background.pdf`, especially when games or rows must be paired as odd vs even or adjacent matchups and the result must be written to `/root/answer.txt`.

## How to Use

1. Read `/root/background.pdf` with `pypdf.PdfReader` text extraction first. Only extract enough text to identify the game-number column and the exact rule for deciding which game won a matchup. Do not render PDF pages or do visual inspection unless text extraction fails.
2. Open `/root/data.xlsx` with `pandas.ExcelFile` to inspect sheet names and a few header rows. Choose the sheet with game-level records, not summary/pivot tabs.
3. Load only the required columns. Normalize headers, coerce the game column to integer, coerce the comparison metric to numeric, and drop blank or summary rows.
4. If the workbook already has a winner/result column and the background explicitly defines it as the game outcome, use that directly. Otherwise sort by game number and pair `(1,2)`, `(3,4)`, `(5,6)`, etc. Odd-numbered games belong to Player 1; even-numbered games belong to Player 2. Ignore an unmatched final odd game.
5. Count a Player 1 match win when the odd-game metric is greater than the even-game metric, a Player 2 match win when the even-game metric is greater, and treat ties as 0 unless the background states otherwise.
6. Compute `(number of Player 1 match wins) - (number of Player 2 match wins)` with vectorized pandas/numpy operations. Sanity-check the first few pairs manually.
7. Write only the final number to `/root/answer.txt` with no label, explanation, or extra formatting.

## Scripts

### pairwise_match_delta.py

```
import argparse\nimport pandas as pd\n\n\ndef solve(xlsx_path, sheet_name, game_col, value_col, answer_path):\n    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, usecols=[game_col, value_col])\n    df = df.rename(columns={game_col: 'game', value_col: 'value'})\n    df['game'] = pd.to_numeric(df['game'], errors='coerce')\n    df['value'] = pd.to_numeric(df['value'], errors='coerce')\n    df = df.dropna(subset=['game', 'value']).copy()\n    df['game'] = df['game'].astype(int)\n    df = df.sort_values('game')\n\n    odd = df[df['game'] % 2 == 1].copy()\n    even = df[df['game'] % 2 == 0].copy()\n    odd['pair'] = (odd['game'] + 1) // 2\n    even['pair'] = even['game'] // 2\n\n    merged = odd[['pair', 'value']].merge(\n        even[['pair', 'value']],\n        on='pair',\n        how='inner',\n        suffixes=('_p1', '_p2')\n    )\n\n    p1_wins = (merged['value_p1'] > merged['value_p2']).sum()\n    p2_wins = (merged['value_p2'] > merged['value_p1']).sum()\n    result = int(p1_wins - p2_wins)\n\n    with open(answer_path, 'w', encoding='utf-8') as f:\n        f.write(str(result))\n\n\nif __name__ == '__main__':\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--xlsx', required=True)\n    parser.add_argument('--sheet', required=True)\n    parser.add_argument('--game-col', required=True)\n    parser.add_argument('--value-col', required=True)\n    parser.add_argument('--answer', default='/root/answer.txt')\n    args = parser.parse_args()\n    solve(args.xlsx, args.sheet, args.game_col, args.value_col, args.answer)\n
```

