# APPLICATIONS — where else this work applies

The dataset, methods, and findings of this project transfer to other fields.
Each entry: what transfers, and a concrete next step.

## 1. Power-grid risk operations (direct)
- **What transfers:** the Dst forecast itself. Grid operators (NERC, utilities)
  take protective action during G4–G5 storms (transformer deloading, canceling
  maintenance on critical lines).
- **Next step:** map predicted Dst to NOAA G-scale + regional geomagnetically
  induced current (GIC) risk using ground-conductivity models; produce a
  utility-facing alert feed.

## 2. Satellite operations & space traffic
- **What transfers:** the same solar-wind drivers inflate the thermosphere,
  increasing drag on LEO satellites (Starlink lost ~40 satellites to a 2022 storm).
- **Next step:** couple the Dst forecast with an atmospheric density model
  (e.g., JB2008) to predict drag windows for conjunction screening.

## 3. Aviation (polar routes)
- **What transfers:** storms degrade HF radio and GPS on polar routes; airlines
  reroute at high cost.
- **Next step:** combine storm forecasts with flight-track data to estimate
  reroute cost vs. radiation/comms risk — an operations-research problem.

## 4. Finance & insurance (catastrophe modeling)
- **What transfers:** extreme space weather is a modeled tail risk (a Carrington-class
  event is estimated at $1–2T). Insurers need event-frequency curves.
- **Next step:** use the 60-year Dst record to fit extreme-value statistics for
  storm intensity; feed into nat-cat models alongside hurricanes/quakes.

## 5. Communications & GNSS resilience
- **What transfers:** ionospheric disturbances from the same drivers disrupt
  GPS/GNSS precision (agriculture, surveying, timing for power/telecom).
- **Next step:** extend the pipeline to predict ROTI/TEC disturbance indices
  from the same OMNI features.

## 6. Climate science (methods transfer)
- **What transfers:** the lag-window + coupling-function feature engineering and
  the time-series validation discipline (no shuffling across time, event-based
  skill scores).
- **Next step:** apply the same pipeline template to ENSO or heatwave
  prediction from SST/atmospheric drivers.

## 7. Epidemiology / public health (methods transfer)
- **What transfers:** rare-event forecasting with heavy class imbalance —
  storms are to Dst what outbreaks are to case counts.
- **Next step:** adapt the POD/FAR event-skill evaluation framework to
  early-warning models for disease outbreaks.

## 8. Education
- **What transfers:** the full pipeline is runnable on a laptop from open data.
- **Next step:** a one-day workshop notebook — "forecast a solar storm before
  lunch" — for heliophysics or data-science courses.
