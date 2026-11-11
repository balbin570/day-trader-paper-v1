"""Atomic snapshot persistence and durable candle-level signal identity."""
import json
import os
import tempfile
from pathlib import Path


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def deduplicate(rows, history):
    seen = set()
    for path in sorted(history.glob('*/*.json')):
        payload = json.loads(path.read_text())  # Corruption must not reset identity.
        seen.update(row['signal_id'] for row in payload.get('signals', []) if row.get('signal_id'))
    for row in rows:
        if row.get('signal') != 'BREAKOUT_WATCH':
            continue
        key = f"{row['strategy_id']}:{row['ticker']}:{row['timestamp_utc']}"
        row['signal_id'] = key
        if key in seen:
            row['signal'] = 'DUPLICATE_SIGNAL'
        seen.add(key)
