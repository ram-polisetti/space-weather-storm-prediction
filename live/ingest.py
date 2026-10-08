"""Observation snapshots only. Never performs model inference."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.request

FEEDS = {
    'mag': ('https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json', ['bz_gsm', 'bt']),
    'wind': ('https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json', ['proton_speed', 'proton_density']),
}
LIMIT = 8 * 1024 * 1024

def timestamp(s):
    if not isinstance(s, str):
        raise ValueError('missing timestamp')
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)

def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def normalize(rows, fields, now):
    if not isinstance(rows, list) or not rows:
        raise ValueError('feed must be a non-empty array')
    out = {}; conflicts = set(); rejected = 0
    for r in rows:
        try:
            if not isinstance(r, dict) or not isinstance(r.get('active'), bool):
                raise ValueError('invalid record')
            if not r['active']:
                continue
            t = timestamp(r.get('time_tag'))
            if t > now + timedelta(minutes=2) or t < now - timedelta(days=2):
                raise ValueError('outside observation window')
            source = r.get('source')
            if not isinstance(source, str) or not source or len(source) > 60:
                raise ValueError('missing source')
            values = {}
            for k in fields:
                v = r.get(k)
                if not number(v) or v <= -999:
                    raise ValueError('missing or sentinel value')
                if k != 'bz_gsm' and v < 0:
                    raise ValueError('negative physical magnitude')
                values[k] = v
            # Quality semantics have not been validated. Display the provider
            # flags verbatim, never label these as scientific-quality accepted.
            flags = {k: v for k, v in r.items() if 'flag' in k or k == 'overall_quality'}
            item = {'time': t.isoformat(), 'source': source, 'values': values, 'provider_flags': flags}
            key = t.isoformat()
            if key in out and out[key] != item:
                conflicts.add(key)
            out[key] = item
        except (ValueError, TypeError, OverflowError):
            rejected += 1
    for key in conflicts:
        out.pop(key, None)
    selected = sorted(out.values(), key=lambda r: r['time'])
    if not selected:
        raise ValueError('no usable active records')
    return selected, rejected, len(conflicts)

def fetch(url):
    error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'space-weather-research-demo/1.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read(LIMIT + 1)
                if len(raw) > LIMIT:
                    raise ValueError('payload limit exceeded')
                return raw, response.status
        except Exception as e:
            error = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError('fetch failed') from error

def snapshot(now, downloader=fetch):
    feeds = {}
    for name, (url, fields) in FEEDS.items():
        raw, status = downloader(url)
        rows, rejected, conflicts = normalize(json.loads(raw), fields, now)
        latest = timestamp(rows[-1]['time'])
        feeds[name] = {'url': url, 'http_status': status, 'sha256': hashlib.sha256(raw).hexdigest(),
                       'latest_observation': latest.isoformat(), 'age_minutes_at_fetch': (now-latest).total_seconds()/60,
                       'stale_at_fetch': now-latest > timedelta(minutes=30), 'rejected': rejected,
                       'conflicting_minutes': conflicts, 'records': rows}
    return {'schema': 1, 'generated_at': now.isoformat(), 'mode': 'observations_only',
            'prediction': {'available': False, 'reason': '260-feature causal and latency bridge not validated'},
            'quality_note': 'Provider flags are shown but not interpreted. These are unvalidated research observations, not quality-certified measurements.',
            'feeds': feeds}

def publish(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, allow_nan=False, separators=(',', ':'))
    if len(raw.encode()) > LIMIT:
        raise ValueError('snapshot limit exceeded')
    temporary = path.with_suffix('.tmp')
    temporary.write_text(raw + '\n')
    os.replace(temporary, path)

def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', default='web/observations.json'); a = p.parse_args()
    publish(a.output, snapshot(datetime.now(timezone.utc)))

if __name__ == '__main__':
    main()
