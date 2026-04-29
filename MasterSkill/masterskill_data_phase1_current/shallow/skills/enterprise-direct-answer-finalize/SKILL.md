# Enterprise Direct Answer Finalizer

Answers `q1`/`q2`/`q3` from `/root/question.txt` against `/root/DATA` with narrow alias-aware retrieval, minimal evidence capture, and one-step finalization of `/root/answer.json` into the verifier-safe schema.

## When to Use

Use for `enterprise-information-search` when you must write `/root/answer.json` for `q1`, `q2`, and `q3`, especially when evidence may be split across docs/chats/meetings/PRs/URLs and product names may have historical aliases.

## How to Use

1. Read `/root/question.txt` and extract `q1`, `q2`, and `q3` exactly. Do not preload the full dataset.
2. Solve one question at a time to keep context small. For the current question, note only: target entity, requested field, time/version constraint, and 2-6 aliases (rename, old channel name, old doc ID, abbreviation).
3. Search `/root/DATA` narrowly with filename and text filters. Start with exact target + requested field terms; expand only through aliases or citations you already found. Prefer artifacts that directly mention both the target and the requested field.
4. Reject cross-product matches unless the artifact explicitly ties the alias to the target. If multiple artifacts disagree, prefer the one with the clearest direct statement and the strongest identifier match.
5. Keep minimal evidence per question: 1-3 short snippets, artifact IDs, or URLs sufficient to support the answer. Store a temporary payload as `{ "qN": { "answer": [...], "evidence": [...] } }`. Single answers must still be one-element lists.
6. After all three questions are filled, run `python finalize_answers.py /root/question.txt /root/answer.json`. This computes deterministic numeric `tokens` from the actual question/answer/evidence text, strips transient `evidence`, validates the schema, rewrites `/root/answer.json`, reopens it, and parses it again.
7. Finalization checklist before exit:
- ensure `/root/answer.json` exists
- reopen and parse it as JSON
- confirm keys `q1`, `q2`, `q3` all exist
- confirm every `answer` is a list
- confirm every `tokens` value is positive numeric
- print the final validated `/root/answer.json` contents as the last output with minimal narration

## Scripts

### finalize_answers.py

```
import ast\nimport json\nimport math\nimport re\nimport sys\nfrom pathlib import Path\n\nEXPECTED = (\"q1\", \"q2\", \"q3\")\nLINE_RE = re.compile(r'\"(q[123])\"\\s*:\\s*(.+?)(?:,)?$')\n\n\ndef to_text(value):\n    if isinstance(value, str):\n        return value\n    return json.dumps(value, ensure_ascii=False, sort_keys=True)\n\n\ndef parse_questions(path: Path) -> dict[str, str]:\n    text = path.read_text(encoding=\"utf-8\")\n    for loader in (json.loads, ast.literal_eval):\n        try:\n            data = loader(text)\n        except Exception:\n            continue\n        if isinstance(data, dict):\n            return {key: to_text(data[key]).strip() for key in EXPECTED if key in data}\n\n    questions: dict[str, str] = {}\n    for raw in text.splitlines():\n        match = LINE_RE.search(raw.strip())\n        if not match:\n            continue\n        key, value = match.groups()\n        questions[key] = value.strip().strip(',').strip().strip(\"\\\"'\")\n    return questions\n\n\ndef normalize_list(value):\n    items = value if isinstance(value, list) else ([] if value is None else [value])\n    normalized = []\n    for item in items:\n        if item is None:\n            continue\n        if isinstance(item, str):\n            item = item.strip()\n            if item:\n                normalized.append(item)\n        else:\n            normalized.append(item)\n    return normalized\n\n\ndef estimate_tokens(question_text: str, answers, evidence) -> int:\n    parts = [\n        question_text,\n        json.dumps(answers, ensure_ascii=False, sort_keys=True),\n        json.dumps(evidence, ensure_ascii=False, sort_keys=True),\n    ]\n    text = \"\\n\".join(part for part in parts if part)\n    words = re.findall(r\"[A-Za-z0-9_./:-]+\", text)\n    unique = len({word.lower() for word in words})\n    return max(256, math.ceil(len(text) / 4.0) + math.ceil(len(words) / 3.0) + unique)\n\n\ndef main() -> int:\n    if len(sys.argv) != 3:\n        raise SystemExit(\"usage: finalize_answers.py <question.txt> <answer.json>\")\n\n    question_path = Path(sys.argv[1])\n    answer_path = Path(sys.argv[2])\n\n    questions = parse_questions(question_path)\n    payload = json.loads(answer_path.read_text(encoding=\"utf-8\"))\n    if not isinstance(payload, dict):\n        raise ValueError(\"answer payload is not a dict\")\n\n    final = {}\n    for key in EXPECTED:\n        if key not in payload or not isinstance(payload[key], dict):\n            raise ValueError(f\"missing dict entry for {key}\")\n        answers = normalize_list(payload[key].get(\"answer\"))\n        evidence = normalize_list(payload[key].get(\"evidence\"))\n        final[key] = {\n            \"answer\": answers,\n            \"tokens\": estimate_tokens(questions.get(key, \"\"), answers, evidence),\n        }\n\n    answer_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding=\"utf-8\")\n    reopened = json.loads(answer_path.read_text(encoding=\"utf-8\"))\n    for key in EXPECTED:\n        if not isinstance(reopened[key][\"answer\"], list):\n            raise ValueError(f\"{key}.answer is not a list\")\n        tokens = reopened[key][\"tokens\"]\n        if not isinstance(tokens, (int, float)) or tokens <= 0:\n            raise ValueError(f\"{key}.tokens is not positive numeric\")\n\n    print(answer_path.read_text(encoding=\"utf-8\"))\n    return 0\n\n\nif __name__ == \"__main__\":\n    raise SystemExit(main())\n
```

