# Enterprise Info Direct Search

Answers batch questions over enterprise datasets by doing targeted local search, minimal evidence reads, and strict JSON output formatting.

## When to Use

Use when questions must be answered from a local enterprise data dump such as /root/DATA and written to a required JSON file with per-question answers and token logging.

## How to Use

1. Read /root/question.txt once and extract every question key and prompt.
2. For each question, pull out the smallest set of search anchors first: exact names, emails, project codenames, ticket IDs, repo names, dates, URLs, or document titles.
3. Search /root/DATA with fast local search only: prefer `rg --files` and `rg -n` to find candidate files and exact passages before opening full files.
4. Open only the top candidate files or matching line ranges needed to answer the question. Do not broadly browse unrelated artifacts.
5. When multiple entities share a name, disambiguate with a second attribute from the question or evidence source before extracting the answer.
6. Extract only the final answer values. If there are multiple values, store them as a list. If there is one value, still store it as a list of length 1.
7. Write /root/answer.json in this exact shape: `{ "q1": {"answer": ["..."], "tokens": "..."}, ... }`.
8. Include a `tokens` string for every question. Use the best available per-question token count or estimate, but never omit the field.
9. Before finishing, validate that every question key is present, every `answer` is a list, and the file is valid JSON readable by Python.

