"""Download OMNI2 hourly solar wind data (CDAWeb HAPI) and Kyoto Dst index.

Writes raw files to data/raw/ and a provenance manifest to data/fetch_manifest.tsv
(columns: fetched_utc, url, http_status, bytes, sha256, kind, note).
"""
import csv
import datetime as dt
import hashlib
import os
import sys
import urllib.request

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
RAW = os.path.normpath(RAW)
MANIFEST = os.path.normpath(os.path.join(RAW, "..", "fetch_manifest.tsv"))

HAPI_BASE = "https://cdaweb.gsfc.nasa.gov/hapi/data"
# NOTE: HAPI requires parameters in the dataset's native order (error 1411 otherwise)
HAPI_PARAMS = ",".join([
    "ABS_B1800", "BY_GSM1800", "BZ_GSM1800",   # IMF (nT)
    "T1800", "N1800", "V1800", "Pressure1800",  # plasma
    "E1800", "Beta1800",                        # derived
    "KP1800", "DST1800",                        # indices (from OMNI feed)
])

YEARS_OMNI = range(2015, 2026)          # 2015..2025
YEARS_DST_FINAL = range(2015, 2021)     # final Dst published through 2020
YEARS_DST_PROV = range(2021, 2026)      # provisional after that


def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"SKIP (exists) {dest}")
        return {"url": url, "http_status": "SKIP", "bytes": os.path.getsize(dest),
                "sha256": hashlib.sha256(open(dest, "rb").read()).hexdigest(),
                "note": "already present from earlier run"}
    req = urllib.request.Request(url, headers={"User-Agent": "space-weather-storm-prediction/0.1 (open science; contact: ram-polisetti)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status, body = r.status, r.read()
    except Exception as e:  # noqa: BLE001 - log and continue; manifest records failure
        print(f"FAIL {url}: {e}", file=sys.stderr)
        return {"url": url, "http_status": "ERR", "bytes": 0, "sha256": "-", "note": str(e)[:120]}
    sha = hashlib.sha256(body).hexdigest()
    with open(dest, "wb") as f:
        f.write(body)
    print(f"OK {url} -> {dest} ({len(body)} bytes)")
    return {"url": url, "http_status": status, "bytes": len(body), "sha256": sha, "note": ""}


def main():
    os.makedirs(RAW, exist_ok=True)
    rows = []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    # 1) OMNI2 hourly via HAPI, one request per year
    for y in YEARS_OMNI:
        url = (f"{HAPI_BASE}?id=OMNI2_H0_MRG1HR"
               f"&time.min={y}-01-01T00:00:00Z&time.max={y + 1}-01-01T00:00:00Z"
               f"&parameters={HAPI_PARAMS}&format=csv&include=header")
        dest = os.path.join(RAW, f"omni2_h0_{y}.csv")
        rec = fetch(url, dest)
        rows.append((now, rec["url"], rec["http_status"], rec["bytes"], rec["sha256"], "omni2_hapi", rec["note"]))

    # 2) Kyoto Dst monthly files (final 2015-2020, provisional 2021-2025)
    for y in YEARS_DST_FINAL:
        kind = "dst_final"
        for m in range(1, 13):
            ym = f"{y}{m:02d}"
            url = f"https://wdc.kugi.kyoto-u.ac.jp/dst_final/{ym}/dst{y % 100:02d}{m:02d}.for.request"
            dest = os.path.join(RAW, "dst_kyoto", f"dst_final_{ym}.txt")
            rec = fetch(url, dest)
            rows.append((now, rec["url"], rec["http_status"], rec["bytes"], rec["sha256"], kind, rec["note"]))
    for y in YEARS_DST_PROV:
        kind = "dst_provisional"
        for m in range(1, 13):
            if y == 2025 and m > 9:
                continue  # data not yet published (today is 2026-09-28; allow lag)
            ym = f"{y}{m:02d}"
            url = f"https://wdc.kugi.kyoto-u.ac.jp/dst_provisional/{ym}/dst{y % 100:02d}{m:02d}.for.request"
            dest = os.path.join(RAW, "dst_kyoto", f"dst_provisional_{ym}.txt")
            rec = fetch(url, dest)
            rows.append((now, rec["url"], rec["http_status"], rec["bytes"], rec["sha256"], kind, rec["note"]))

    new_file = not os.path.exists(MANIFEST)
    with open(MANIFEST, "a", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if new_file:
            w.writerow(["fetched_utc", "url", "http_status", "bytes", "sha256", "kind", "note"])
        w.writerows(rows)
    ok = sum(1 for r in rows if str(r[2]) == "200")
    print(f"\n{ok}/{len(rows)} fetches OK -> {MANIFEST}")


if __name__ == "__main__":
    main()
