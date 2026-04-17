import json
import math
import re
import sys
from pathlib import Path

QUESTION_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')


def parse_questions(path: Path) -> dict[str, str]:
    questions: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        match = QUESTION_RE.search(raw_line.strip())
        if match:
            key, text = match.groups()
            questions[key] = text.strip().rstrip(',')
    return questions


def estimate_tokens(question_text: str, answers: list[str]) -> int:
    blob = json.dumps(answers, ensure_ascii=False, separators=(',', ':'))
    chars = len(question_text) + len(blob)
    return max(32, int(math.ceil(chars / 4.0)) + 48)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: finalize_answer.py <question.txt> <answer.json>')
        return 2

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    if not question_path.exists():
        print(f'missing question file: {question_path}')
        return 1
    if not answer_path.exists():
        print(f'missing answer file: {answer_path}')
        return 1

    questions = parse_questions(question_path)
    payload = json.loads(answer_path.read_text(encoding='utf-8'))

    if not isinstance(payload, dict):
        raise ValueError('answer payload is not a dict')

    normalized = {}
    for key in ('q1', 'q2', 'q3'):
        entry = payload.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f'{key} entry is not a dict')
        answers = entry.get('answer')
        if not isinstance(answers, list):
            raise ValueError(f'{key}.answer is not a list')
        normalized_answers = []
        for item in answers:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized_answers.append(text)
        normalized[key] = {
            'answer': normalized_answers,
            'tokens': estimate_tokens(questions.get(key, ''), normalized_answers),
        }

    encoded = json.dumps(normalized, ensure_ascii=False, indent=2)
    answer_path.write_text(encoded, encoding='utf-8')

    reparsed = json.loads(answer_path.read_text(encoding='utf-8'))
    for key in ('q1', 'q2', 'q3'):
        if key not in reparsed:
            raise ValueError(f'missing key: {key}')
        if not isinstance(reparsed[key].get('answer'), list):
            raise ValueError(f'{key}.answer is not a list after rewrite')
        if not isinstance(reparsed[key].get('tokens'), (int, float)) or reparsed[key]['tokens'] <= 0:
            raise ValueError(f'{key}.tokens invalid after rewrite')

    print('answer contract OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
