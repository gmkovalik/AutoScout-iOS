"""Google Sheets sync for AutoScout scouting notes via a deployed Apps Script web app."""
from __future__ import annotations
import json
import urllib.request

def sync_notes(endpoint: str, notes_by_match: dict) -> dict:
    """Push local notes, receive the shared sheet, and merge into match-keyed notes."""
    rows = []
    for match, notes in (notes_by_match or {}).items():
        for note in notes:
            row = dict(note)
            row['match'] = str(match)
            if not row.get('id'):
                import uuid
                row['id'] = uuid.uuid4().hex
            rows.append(row)
    payload = json.dumps({'action': 'sync', 'notes': rows}).encode('utf-8')
    request = urllib.request.Request(endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode('utf-8'))
    merged = {}
    for note in result.get('notes', []):
        match = str(note.get('match') or 'General')
        clean = {key: note.get(key) for key in ('id', 'team', 'category', 'text', 'pinned', 'created_at')}
        merged.setdefault(match, []).append(clean)
    return merged
