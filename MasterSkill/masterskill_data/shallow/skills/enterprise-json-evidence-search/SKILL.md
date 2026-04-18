# Enterprise JSON Evidence Search

Answers multi-question enterprise dataset queries by doing narrow local evidence search over /root/DATA and writing a strict /root/answer.json with list-normalized answers and per-question token strings.

## When to Use

Use when a task provides a local enterprise corpus plus a question file and requires exact JSON output at a fixed path, especially when answers require multi-hop lookup across docs, chats, meetings, PRs, or directories.

## How to Use

1. Read only /root/question.txt first and extract every question key.
2. For each question, identify the minimum unique anchors to search for: people, teams, projects, dates, repo names, ticket IDs, products, or phrases.
3. Search /root/DATA with narrow local queries first (prefer filename and keyword filtering); do not load large files or broad corpus chunks unless the first pass leaves ambiguity.
4. Follow only the top candidate artifacts and do second-hop lookup only when needed to connect an entity to the requested field.
5. Before finalizing, explicitly disambiguate similar names, products, or organizations so evidence stays on the same entity/thread.
6. Normalize every answer to a list of strings, even for one item.
7. Build /root/answer.json in this exact shape: {"q1":{"answer":["..."],"tokens":"..."}, ...}. Tokens must always be a string for every question.
8. Write the JSON file before ending, and validate that all question keys exist, every answer is a list, and every tokens value is a string.

