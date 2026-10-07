# Fresh historical hindcast: October 7, 2026

This replaces the pre-repair performance record. NASA OMNI2 and Kyoto Dst were downloaded again (140 HTTP-200 files), then the repaired dataset, full original grid, classifiers and evaluation were rerun. This is a retrospective hindcast, not a live 2026 storm forecast or an operational alert system.

Dataset: 94,223 rows, 269 columns, from 2015-01-01 00:00:00+00:00 through 2025-09-30 22:00:00+00:00. Observed Dst <= -50: 2,933 hours; <= -100: 366.

## Method and splits

260 features, with future Dst labels and OMNI Dst/Kp excluded. Missing UTC hours are restored and unknown future labels are excluded. Six forecast hours are purged at each split boundary. Training: 2015-2018 (34,888 rows); validation: 2019 (8,682); test: 2020 (8,772); provisional-data extra split: 2021-2024 (34,099), ending before January 1, 2025. Downloaded 2025 rows are not included in the scored extra split.

All 44 original regression candidates were fit: 4 Ridge and 18 histogram-gradient-boosting candidates per horizon. Validation RMSE picks the winner in original candidate order; ties keep the first. Two original balanced classifiers were fit separately. No grid reduction, synthetic data or altered random seed. Checkpointing changes execution granularity, not the method.

## Regression

RMSE and MAE are in nT. Persistence carries the current observed Dst forward.

### +1h: ridge_a10.0

| Split | Rows | Persistence RMSE | Model RMSE | Persistence MAE | Model MAE |
|---|---:|---:|---:|---:|---:|
| val | 8682 | 2.92 | 2.39 | 2.07 | 1.78 |
| test | 8772 | 2.83 | 2.31 | 2.03 | 1.73 |
| extra | 34099 | 4.58 | 3.55 | 2.88 | 2.34 |

### +6h: gbm_100it_lr0.05_leaf63

| Split | Rows | Persistence RMSE | Model RMSE | Persistence MAE | Model MAE |
|---|---:|---:|---:|---:|---:|
| val | 8682 | 7.8 | 6.28 | 5.65 | 4.63 |
| test | 8772 | 7.73 | 6.44 | 5.62 | 4.7 |
| extra | 34099 | 13.54 | 12.22 | 8.26 | 7.47 |

## Storm-hour classification

Threshold: probability >= 0.5. These are hour-level counts, not independent storm-event trials. POD is detection probability; FAR is the false-alarm ratio; CSI is critical success index.

| Future minimum | Split | Positive hours | TP | FP | FN | POD | FAR | CSI |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| storm50_6h | val | 78 | 47 | 37 | 31 | 0.603 | 0.44 | 0.409 |
| storm50_6h | test | 55 | 28 | 23 | 27 | 0.509 | 0.451 | 0.359 |
| storm50_6h | extra | 1777 | 1379 | 471 | 398 | 0.776 | 0.255 | 0.613 |
| storm100_6h | val | 0 | 0 | 0 | 0 | not defined | not defined | not defined |
| storm100_6h | test | 0 | 0 | 0 | 0 | not defined | not defined | not defined |
| storm100_6h | extra | 291 | 132 | 101 | 159 | 0.454 | 0.433 | 0.337 |

No intense-storm positive hours occur in validation/test, so their intense-storm detection skill cannot be estimated there. The extra split has 291 positive hours, but uses provisional Dst. Probability scores are not claimed calibrated.

## Case plots and limits

2015/2017 plots are training-period illustrations, not held-out results. May 2024 is in the extra split. The residual histogram includes training years and is not a held-out performance distribution. All four regenerated PNGs were visually inspected for readable axes/legends and clipping.

| Case | Observed minimum | Predicted +6h minimum | Maximum storm score |
|---|---:|---:|---:|
| 2015-03-17_st-patricks | -234.0 | -198.6 | 1.0 |
| 2017-09-08_sep2017 | -148.0 | -116.0 | 1.0 |
| 2024-05-11_gannon | -406.0 | -181.3 | 1.0 |

The May 2024 point forecast misses much of the superstorm depth (-181.3 predicted minimum vs -406 observed). The maxima are not paired onset-time errors. Low average error and a high storm score do not establish safe grid/satellite decisions. OMNI and Kyoto are retrospective products, provisional targets may change, hours are correlated, intense storms are rare, and no real-time latency or uncertainty/calibration evaluation was done. The prior six integrity tests pass; they do not establish production readiness.

## Reproduce and provenance

Use the normal download/build/train/evaluate commands in README. If a foreground execution limit interrupts the grid, run `python src/rerun_checkpointed.py` until it reports all candidates complete, then `python src/finalize_rerun.py` and `python src/evaluate.py`. Checkpoints must match the dataset SHA; finalization uses original scoring, permutation importance and classifiers. Checkpoint model binaries and processed data remain excluded from git. `results/fresh-fetch-manifest.tsv` isolates this download from historical manifest rows. `results/fresh-rerun-provenance.json` records environment, source/output hashes and candidate scores. No model installation/deployment, production alert or new external recipient was configured.

## Plot delivery caveat for this branch

The four fresh PNGs are in the separately delivered checked review archive. Binary web uploads are blocked at commit, so this text-only review branch leaves old repository PNGs in place. Those old PNGs are NOT the fresh outputs described above. Do not cite them as evidence for this rerun.
