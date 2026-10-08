# Historical storm evidence view

This view aligns three retrospective measurements with the existing frozen-model replay. It makes no live forecasts, risk score, causal discovery claim or accuracy-gain claim.

- Solar wind: checked October 7 OMNI hourly Bz GSM and bulk speed, plotted at their native half-hour midpoint. Fill sentinels become missing values. Southward Bz is shaded, not converted into a risk score.
- Ground response: GFZ definitive Kp and ap fetched directly for the 2015, 2017 and 2024 event windows. Kp bars cover their actual UTC three-hour intervals; ap is drawn as an interval step. All records are definitive. No preliminary or live Kp is displayed.
- Storm depth: existing attributed rendered Dst/frozen +6h model curves, with target-valid timestamps and origin six hours earlier. Missing replay hours break the line. No raw Dst values are in the site's JSON or code.

A shared selected-time marker follows the slider. The selected-time text reads only solar wind and Kp/ap measurements; it does not interpolate Dst, imply future availability or estimate danger. Historical timestamps are separate from the current NOAA snapshot and its age.

The 2015 and 2017 examples overlap model training. May 2024 is from the extra 2021–2024 scoring period. Kp, southward Bz and coupling terms already appear in the model inputs: this display is corroborating storm evidence, not a new predictor or independent validation.

## Provenance and licenses

`web/evidence.json` contains only OMNI solar-wind columns, GFZ Kp/ap and provenance hashes. Three attributed composite scientific figures are embedded in `web/index.html`; no extra image files or raw historical Dst packet are deployed. Figure SHA-256 values bind the metadata to the embedded images.

GFZ data: CC BY 4.0, attribution GFZ Helmholtz Centre for Geosciences. Our changes are selection, plotting, interval alignment and combination with other sources. DOI 10.5880/Kp.0001. Kp/ap are distinct from the bundled sunspot column, which is not imported.
- https://kp.gfz.de/en/
- https://kp.gfz.de/en/data
- https://creativecommons.org/licenses/by/4.0/
- https://doi.org/10.5880/Kp.0001

Direct queries use `https://kp.gfz.de/app/json/`, `index=Kp` or `index=ap`, `status=def`, and these exclusive-window selections:
- March 15–20, 2015
- September 6–12, 2017
- May 9–15, 2024

The figures clip to the exact existing replay window; full bin values are preserved when a bin intersects the boundary. Input JSON remains the provider's interval-start semantics. API response and OMNI source-file hashes are recorded in the packet.

OMNI solar wind: NASA GSFC/SPDF. SPASE metadata names NASA heliophysics public data products as CC0, but that does not remove source-provider restrictions on third-party geomagnetic indices. Only solar-wind columns are included as raw values.
- https://spase-metadata.org/NASA/NumericalData/OMNI/PT1H
- https://omniweb.gsfc.nasa.gov/html/citing.html

Dst: WDC for Geomagnetism, Kyoto; DOI 10.17593/14515-74000. The existing scientific-figure-only boundary remains. No raw Dst packet, quicklook Dst, commercial data rights or blanket MIT license is granted.

## Deployment and failure behavior

Existing NOAA ingestion and four-daily schedule remain unchanged. Historical Kp/ap are fixed local assets; visitors and scheduled jobs do not query GFZ. No new API key, external runtime request, runner tier, paid service or model/retraining action. The workflow runs the additional evidence tests before fetch/deployment. Failure still preserves the last deployed complete site.

Missing `evidence.json` disables the selected-time text/slider, with an explicit message; embedded scientific figures remain visible. Missing current observations do not hide historical evidence. Mobile figures have intentional horizontal scrolling with a 900px minimum width so axis labels remain readable.
