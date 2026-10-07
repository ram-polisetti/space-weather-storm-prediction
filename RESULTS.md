# RESULTS — space-weather storm prediction

Two independent open data sources: NASA OMNI2 solar-wind/IMF (via CDAWeb HAPI)
and Kyoto WDC Dst (final 2015–2020, provisional 2021–Sep 2025). 94,223 hourly
rows, 2015-01-01 to 2025-09-29. 2,933 storm hours (Dst <= -50 nT), 366 intense
hours (Dst <= -100 nT). Deepest minimum: -406 nT on 2024-05-11 (Gannon superstorm).

## Reproduction status

The numbers below are historical results from the original run, not results
from the time-integrity repair. They must be recomputed before comparison:
the repaired pipeline restores missing UTC hours, requires all future labels
to be known, and purges six forecast hours at each split boundary. The 2015
and 2017 case plots are training-period illustrations, not held-out forecasts.
The residual summary and histogram include training years and must not be
read as held-out test error. OMNI and final/provisional Dst are retrospective
products, so this is a hindcast, not proof of real-time operational skill.

## Method

**Targets.** Kyoto Dst at +1h and +6h (regression); storm events defined as
min Dst over the next 6h <= -50 / -100 nT (classification).

**Features (260).** OMNI2 IMF/plasma (B, By/Bz GSM, V, N, T, pressure, E, beta),
southward-Bz magnitude, Newell coupling function, plus Dst history: lags at
1/3/6/12/24h, hourly changes, rolling means/mins over 3/6/12/24h — each with
3/6/12h rolling mean/min/max windows.

**Splits (strictly by time, no shuffling).** Train 2015–2018, validation 2019,
test 2020 (final Dst), extra 2021–2025 (provisional Dst, includes the May 2024
superstorm — an out-of-distribution stress test).

**Models.** Persistence (current Dst carried forward), Ridge, and
HistGradientBoosting (regression + balanced classifiers). Hyperparameters
chosen on the validation split by grid search.

## Results (final, after iteration 2)

RMSE/MAE in nT. Model hyperparameters were selected on the 2019 validation
split; test = 2020 final Dst; extra = 2021–2025 provisional Dst.

### Dst at +1h (best: Ridge, alpha=10)

| split | n | persistence RMSE | model RMSE | persistence MAE | model MAE |
|---|---|---|---|---|---|
| val 2019 | 8,688 | 2.92 | 2.39 | 2.07 | 1.78 |
| test 2020 | 8,778 | 2.83 | 2.31 | 2.03 | 1.73 |
| extra 2021–25 | 34,105 | 4.58 | 3.55 | 2.89 | 2.35 |

### Dst at +6h (best: HistGradientBoosting, 100 iters, lr 0.05, 31 leaves)

| split | n | persistence RMSE | model RMSE | persistence MAE | model MAE |
|---|---|---|---|---|---|
| val 2019 | 8,688 | 7.80 | 6.31 | 5.65 | 4.66 |
| test 2020 | 8,778 | 7.73 | 6.41 | 5.61 | 4.69 |
| extra 2021–25 | 34,105 | 13.54 | 12.14 | 8.26 | 7.46 |

Top +6h features (permutation importance): recent Dst minimum (`dst_min3h`),
hourly Dst change (`dst_d1h`), Newell solar-wind coupling, recent solar-wind
temperature and pressure maxima. Physically sensible: storm onset is driven by
the solar wind, but the current Dst level and its slope carry most of the
6-hour predictability.

### Storm-event classification (min Dst over next 6h)

| task | split | storm hours | POD | FAR | CSI |
|---|---|---|---|---|---|
| <= -50 nT | val | 78 | 0.56 | 0.41 | 0.41 |
| <= -50 nT | test | 55 | 0.46 | 0.44 | 0.33 |
| <= -50 nT | extra | 1,777 | 0.76 | 0.25 | 0.60 |
| <= -100 nT | extra | 291 | 0.29 | 0.63 | 0.19 |
| <= -100 nT | val/test | 0 | — | — | — (no intense-storm hours in 2019–2020) |

The event classifier is strongest exactly where it matters: during the
storm-rich 2021–2025 period (POD 0.76, FAR 0.25 for moderate storms).
Intense storms (<= -100 nT) remain hard: only 212 such hours in the entire
training set, and the May 2024 superstorm is far outside the training
distribution.

### Case studies (see `results/case_*.png`)

| storm | observed min Dst | model min Dst@+6h | max P(storm in 6h) |
|---|---|---|---|
| 2015-03-17 St. Patrick's | -234 | -198 | 1.00 |
| 2017-09-08 | -148 | -117 | 1.00 |
| 2024-05-11 Gannon | -406 | -178 | 1.00 |

The detector fires with probability 1.0 on all three storms, including
Gannon — but the point forecast underpredicts Gannon's depth by ~230 nT.
The model has never seen a -400 nT storm; this is the honest limit of
training on 2015–2018.

## Limitations

1. Provisional Dst (2021–2025) will be revised by Kyoto; the "extra" split
   numbers may shift slightly when final data lands.
2. OMNI2 has data gaps (spacecraft coverage); rows with <50% core-driver
   coverage are dropped (~1.3% of hours).
3. Intense-storm recall is weak (POD 0.29 at <= -100 nT) — rare-event problem,
   needs more storm examples or physics-informed augmentation.
4. +6h point forecasts underpredict unprecedented superstorm depths.
5. No CME-imagery inputs; a model with coronagraph data would see storms
   coming 1–3 days out instead of hours.

## Iteration log

- **Build 1:** solar-wind features only. +6h RMSE barely beat persistence
  (8.0 vs 8.08 nT) — Dst history was the missing signal.
- **Iteration 1:** added Dst lags/changes/rolling stats; fixed a Newell
  coupling NaN bug (`sin^(8/3)` of negative values). +6h test RMSE ~3.8
  (with an undetected target-leakage feature — see Iteration 2).
- **Iteration 2 (rework pass):** leakage audit caught `dst_nextmin6h`
  (built from future Dst) in the feature set — removed, with an assertion
  guard; honest +6h test RMSE is 6.41. Replaced the flawed event skill
  (thresholded point forecast vs the *past*-6h minimum) with dedicated
  storm-event classifiers. Added validation grid search; best +1h model is
  Ridge (alpha=10), best +6h is a small GBM (100 iters, lr 0.05, 31 leaves).
