# Research dashboard v1
Current NOAA active-source observations, four snapshots daily, plus immutable historical replay. No model inference, retraining, recipients or warnings. Code is MIT; NOAA records remain attributed to NOAA and no endorsement is implied.

The ingestion checks schema, active/source fields, finite physical values, duplicates and timestamp bounds. Provider flags are preserved but their scientific semantics are NOT validated. The page says so. This is basic display validation, not quality-certified data. Missing minutes are not invented, source transitions break curves, and stale status is computed client-side even if scheduled jobs stop.

Magnetic/plasma feeds are separate observations. UTC timestamps are preserved. The observation window is at most two days and fetch payload/snapshot is capped at 8 MiB. Each attempt has bounded retries. No persistent archive/history cache exists in v1: each successful run replaces the full snapshot, and a failed run does not deploy. GitHub schedules can delay/drop runs. Four daily refreshes are not continuous monitoring.

Replay values were computed from the checked October 8 immutable model generation and October 7 dataset. Predictions use the stored 260-feature order, no refitting. Chart x is target valid time (+6h), not inference origin. 2015 and 2017 are training-era illustrations; May 2024 is held-out extra-period evidence. The -181.3 versus -406 minima are separate minima, not paired timing errors. Full original plots/outputs remain attachment-delivered; this page uses a compact derived numeric replay, not old repo PNGs.

No local-attribution panel is claimed in v1. Live prediction/explanations stay off pending the causal feature/latency bridge. This site predicts neither solar flares nor operational impacts.

NOAA feed links:
- https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json
- https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json
- https://www.weather.gov/media/notification/pdf_2026/scn26-21_Data_Format_Changes_Impacting_SWPC_Products.pdf
- https://www.weather.gov/disclaimer

Deployment proposal: existing public repository; GitHub Pages from Actions; standard runner only; 00:17/06:17/12:17/18:17 UTC plus manual trigger. No domain purchase or paid service. Public deployment requires review of page and configuration first. Commit immutable replay JSON once, not raw datasets/models; no private paper material. A workflow on a review branch does not install the schedule, which runs only on main.
