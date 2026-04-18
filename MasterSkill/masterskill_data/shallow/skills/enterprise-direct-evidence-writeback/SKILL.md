# Enterprise Direct Evidence Writeback

Answers enterprise-information-search tasks by doing narrow evidence-first retrieval over /root/DATA, expanding aliases only when explicitly supported by artifacts, and writing verifier-safe list-normalized answers plus actual numeric token usage to /root/answer.json.

## When to Use

Use when the task asks for q1/q2/q3 from /root/question.txt against /root/DATA and requires /root/answer.json with answer lists and positive numeric token fields.

## How to Use

1. Read /root/question.txt and enumerate q1, q2, and q3.
2. For each question, extract the smallest search seed set first: exact product name, IDs, owners, dates, channels, or doc titles mentioned in the question.
3. Search /root/DATA narrowly with those seeds; do not read the full corpus. Open only the top candidate artifacts.
4. Expand aliases only after an artifact explicitly shows a rename, old channel name, predecessor doc ID, or alternate spelling. Re-search with the confirmed alias set, not speculative variants.
5. Prefer canonical evidence first: documents/urls for stable facts, slack/meeting transcripts for decisions or renames, PRs for IDs or implementation confirmation. Cross-check enough context to avoid near-match or cross-product leakage.
6. Extract only the requested names/items/ids. Store every answer as a list, including singletons.
7. Track actual consumed tokens per question from real usage accounting in the solve path; never use guessed placeholders or a copied constant. Tokens must be positive numeric values.
8. Write /root/answer.json exactly as {"q1":{"answer":[...],"tokens":number},"q2":{"answer":[...],"tokens":number},"q3":{"answer":[...],"tokens":number}}.
9. Finalization checklist: write the file, reopen it, parse it as JSON, verify q1/q2/q3 all exist, verify every answer is a list, verify every tokens field is a positive number, and confirm the file is not truncated before exiting.

## Scripts

### validate_answer_contract.py

```
import json\nimport sys\nfrom pathlib import Path\n\n\ndef main() -> int:\n    if len(sys.argv) != 2:\n        print('usage: validate_answer_contract.py <answer.json>')\n        return 2\n\n    answer_path = Path(sys.argv[1])\n    if not answer_path.exists():\n        print(f'missing file: {answer_path}')\n        return 1\n\n    payload = json.loads(answer_path.read_text(encoding='utf-8'))\n    expected = ('q1', 'q2', 'q3')\n\n    if not isinstance(payload, dict):\n        print('answer payload is not a dict')\n        return 1\n\n    for key in expected:\n        if key not in payload:\n            print(f'missing key: {key}')\n            return 1\n        entry = payload[key]\n        if not isinstance(entry, dict):\n            print(f'{key} entry is not a dict')\n            return 1\n        if 'answer' not in entry or 'tokens' not in entry:\n            print(f'{key} missing answer or tokens')\n            return 1\n        if not isinstance(entry['answer'], list):\n            print(f'{key}.answer is not a list')\n            return 1\n        tokens = entry['tokens']\n        if not isinstance(tokens, (int, float)):\n            print(f'{key}.tokens is not numeric')\n            return 1\n        if tokens <= 0:\n            print(f'{key}.tokens must be positive')\n            return 1\n\n    print('answer contract OK')\n    return 0\n\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n
```

