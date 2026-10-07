# Real storm-data fixtures

Downloaded October 6, 2026, over HTTPS from the original providers. CSV line endings are normalized to LF; numeric records are unchanged. These
are actual records, not generated observations. Kyoto's provisional values
may change in later revisions. Offline CI uses these fixed bytes, never a
fresh network request.

- `omni2_h0_2024.csv`: NASA SPDF CDAWeb `OMNI2_H0_MRG1HR`, May 8-15, 2024
  (168 hourly records, including native HAPI metadata and fill values).
  Source: https://cdaweb.gsfc.nasa.gov/hapi/data?id=OMNI2_H0_MRG1HR&time.min=2024-05-08T00:00:00Z&time.max=2024-05-15T00:00:00Z&parameters=ABS_B1800,BY_GSM1800,BZ_GSM1800,T1800,N1800,V1800,Pressure1800,E1800,Beta1800,KP1800,DST1800&format=csv&include=header
  SHA-256: `37573d38f19891c1b747e4b110958f981801000e83a221095bc54afbfd797ab6`
- `dst_provisional_202405.txt`: Kyoto WDC provisional hourly Dst, May 2024
  (744 hourly records; Gannon storm minimum -406 nT).
  Source: https://wdc.kugi.kyoto-u.ac.jp/dst_provisional/202405/dst2405.for.request
  SHA-256: `f2bd464a586e66eb95dd431c5cd864b2c8e180df89eb2d53522fea68ae97f4f7`

Metadata reference: https://cdaweb.gsfc.nasa.gov/hapi/info?id=OMNI2_H0_MRG1HR
Dataset documentation: https://omniweb.gsfc.nasa.gov/html/ow_data.html

One test deliberately removes an actual record to check gap handling. It
creates no replacement measurement. Date split tests divide the same actual
storm slice; those slices are integrity tests, not model-performance claims.

Original provider CSV SHA-256 before CRLF-to-LF normalization: `9041223111268b6f9de12656315f56096a1612566e8f8347c4ec4572a761c87a`.
