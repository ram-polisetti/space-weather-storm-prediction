# space-weather-storm-prediction

Predict geomagnetic storm intensity (Dst index) from upstream solar wind
telemetry with 1–6 hour lead time — an open-science ML pipeline.

## Why
Grid and satellite operators use Dst/Kp forecasts to take protective action
(transformer load management, satellite safe-moding). This project builds a
reproducible hindcast pipeline evaluated against persistence on real storm
events, using open NASA and Kyoto data. Historical performance is recorded
in RESULTS.md and needs recomputation after pipeline repairs.

## Data provenance
| Dataset | Source | Access |
|---|---|---|
| OMNI2 hourly solar wind (IMF Bz, By, \|B\|, Vsw, proton density/temp, dynamic pressure, Kp, Dst) | NASA CDAWeb HAPI, dataset `OMNI2_H0_MRG1HR` | `https://cdaweb.gsfc.nasa.gov/hapi/data?id=OMNI2_H0_MRG1HR&...` (HTTPS; parameters must be requested in dataset-native order) |
| Dst index (hourly, target) | WDC for Geomagnetism, Kyoto | final: `https://wdc.kugi.kyoto-u.ac.jp/dst_final/YYYYMM/dstYYMM.for.request`; provisional: `.../dst_provisional/YYYYMM/...` |
| Storm framing | Dst ≤ −50 nT events identified from the Dst series; cross-checked vs NOAA SWPC archives |

Every download is logged in `data/fetch_manifest.tsv` with UTC timestamp,
HTTP status, byte count, SHA-256 hash, and final URL.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce
```bash
python src/download.py      # fetch OMNI2 + Dst, writes data/fetch_manifest.tsv
python src/build_dataset.py # parse, align, engineer features -> data/processed/
python src/train.py         # baselines + gradient boosting, time-based split
python src/evaluate.py      # metrics + storm case plots -> results/
```

## Integrity checks

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The offline tests use downloaded NASA OMNI and Kyoto records from the May
2024 storm, with exact source URLs and SHA-256 hashes in
[`tests/fixtures/README.md`](tests/fixtures/README.md). Missing hours stay
missing; no synthetic values or interpolation are used. Forecast labels must
remain inside their time split, and unknown labels are not non-storm examples.

## Results
See [`RESULTS.md`](RESULTS.md) — regression + storm-event metrics with honest
limitations, case studies for the 2015, 2017, and 2024 storms (plots in
`results/`).

## Multidisciplinary applications
See [`APPLICATIONS.md`](APPLICATIONS.md) — power grids, satellite ops,
aviation, finance/insurance, GNSS, climate methods, epidemiology, education.

## License
MIT — see `LICENSE`.
