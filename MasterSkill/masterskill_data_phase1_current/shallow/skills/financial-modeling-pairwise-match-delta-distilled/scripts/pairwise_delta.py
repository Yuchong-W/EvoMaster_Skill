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
