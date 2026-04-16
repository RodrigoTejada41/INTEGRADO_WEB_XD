from __future__ import annotations

from pathlib import Path


def infer_file(path: Path, text: str) -> tuple[str, float, dict]:
    ext = path.suffix.lower()
    lines = text.splitlines()

    if ext == '.md':
        headings = [l for l in lines if l.strip().startswith('#')]
        parser = 'markdown-structure'
        confidence = 0.94
        payload = {
            'headings_count': len(headings),
            'first_heading': headings[0].strip() if headings else None,
            'line_count': len(lines),
        }
        return parser, confidence, payload

    if ext == '.json':
        parser = 'json-structure'
        confidence = 0.97
        payload = {
            'line_count': len(lines),
            'starts_with': text[:80],
        }
        return parser, confidence, payload

    parser = 'text-generic'
    confidence = 0.70
    payload = {
        'line_count': len(lines),
        'preview': text[:120],
    }
    return parser, confidence, payload
