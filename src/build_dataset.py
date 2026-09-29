"""Parse raw OMNI2 + Kyoto Dst downloads into a modeling-ready hourly dataset.

- OMNI2 HAPI CSVs: fill values (>=9000 sentinel) -> NaN.
- Kyoto Dst monthly ASCII: DST<YY><MM>*<DD> rows -> hourly series.
- Merge on UTC hour; engineer lag-window features + coupling functions.
- Targets: Dst at +1h and +6h (Kyoto series, authoritative).
- Output: data/processed/dataset.parquet + data/processed/feature_dictionary.csv
"""
import glob
import os
import re

import numpy as np
import pandas as pd

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RAW = os.path.join(BASE, "data", "raw")
PROC = os.path.join(BASE, "data", "processed")

FILL_SENTINEL = 9000.0  # OMNI2 hourly fill values are 9999.x variants


def load_omni():
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "omni2_h0_*.csv"))):
        with open(path) as f:
            lines = f.readlines()
        # HAPI csv with include=header: comment lines start with '#'; the header
        # block documents each parameter's fill value, e.g. #"fill": "999.9"
        header_idx = next(i for i, l in enumerate(lines) if not l.startswith("#"))
        fills = {}
        for l in lines[:header_idx]:
            m = re.search(r'"name":\s*"([^"]+)"', l)
            mf = re.search(r'"fill":\s*"([^"]+)"', l)
            # name and fill appear on adjacent comment lines; pair by order
            if m:
                pending = m.group(1)
            if mf and pending:
                try:
                    fills[pending] = float(mf.group(1))
                except ValueError:
                    pass
                pending = None
        df = pd.read_csv(path, skiprows=header_idx, header=None,
                         names=["Time", "ABS_B1800", "BY_GSM1800", "BZ_GSM1800",
                                "T1800", "N1800", "V1800", "Pressure1800",
                                "E1800", "Beta1800", "KP1800", "DST1800"])
        for col, fill in fills.items():
            if col in df.columns and col != "Time":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].mask(df[col] >= fill * 0.999)
        frames.append(df)
    omni = pd.concat(frames, ignore_index=True)
    omni["Time"] = pd.to_datetime(omni["Time"], utc=True).dt.floor("h")  # half-hour midpoint -> hour
    omni = omni.drop_duplicates("Time").sort_values("Time").reset_index(drop=True)
    return omni


def load_kyoto_dst():
    recs = []
    # Fixed-width format: 'DST<YY><MM>*<DD>' (10 ch) + '  X220   0' (10 ch),
    # then 24 hourly values in I4 (4 chars each). Negative values run together
    # without separators, so split-based parsing fails.
    pat = re.compile(r"^DST(\d{2})(\d{2})\*(\d{2})")
    for path in sorted(glob.glob(os.path.join(RAW, "dst_kyoto", "*.txt"))):
        with open(path, errors="replace") as f:
            for line in f:
                m = pat.match(line)
                if not m:
                    continue
                yy, mm, dd = m.groups()
                # Fixed-width format: 'DST<YY><MM>*<DD>' (10 ch) + '  X220   0' (10 ch),
                # then 24 hourly values in I4 (4 chars each), starting at 0-indexed pos 20.
                chunks = [line[20 + 4 * h:24 + 4 * h] for h in range(24)]
                try:
                    vals = [float(c) for c in chunks]
                except ValueError:
                    continue
                year = 2000 + int(yy)
                base = pd.Timestamp(year=year, month=int(mm), day=int(dd), tz="UTC")
                for h, v in enumerate(vals):
                    # Kyoto uses 9999 for missing
                    recs.append((base + pd.Timedelta(hours=h), np.nan if v >= 9000 else v))
    dst = pd.DataFrame(recs, columns=["Time", "dst_kyoto"]).drop_duplicates("Time")
    return dst.sort_values("Time").reset_index(drop=True)


def add_features(df):
    df = df.copy()
    bz = df["BZ_GSM1800"]
    # Southward Bz magnitude (driver of storms)
    df["bz_south"] = (-bz).clip(lower=0)
    # Newell coupling function dPhi/dt ~ V^(4/3) * Bt^(2/3) * sin^(8/3)(theta/2)
    # (abs on the sine term: fractional power of a negative is undefined in reals)
    by, v = df["BY_GSM1800"], df["V1800"]
    bt = np.sqrt(by**2 + bz**2)
    theta = np.arctan2(by, bz)  # clock angle
    df["newell"] = (v ** (4 / 3)) * (bt ** (2 / 3)) * (np.abs(np.sin(theta / 2)) ** (8 / 3)) / 1e4
    df["ey"] = df["E1800"]  # dawn-dusk electric field proxy as provided
    # Dst history: the single most predictive signal (persistence + recovery dynamics)
    dst = df["dst_kyoto"]
    df["dst_lag1h"] = dst.shift(1)
    df["dst_lag3h"] = dst.shift(3)
    df["dst_lag6h"] = dst.shift(6)
    df["dst_lag12h"] = dst.shift(12)
    df["dst_lag24h"] = dst.shift(24)
    df["dst_d1h"] = dst - df["dst_lag1h"]        # hourly change (main-phase slope)
    df["dst_d6h"] = dst - df["dst_lag6h"]
    for w in (3, 6, 12, 24):
        roll = dst.rolling(window=w, min_periods=max(1, w // 2))
        df[f"dst_mean{w}h"] = roll.mean().values
        df[f"dst_min{w}h"] = roll.min().values
    feat_base = ["BZ_GSM1800", "BY_GSM1800", "ABS_B1800", "V1800", "N1800",
                 "T1800", "Pressure1800", "Beta1800", "bz_south", "newell", "ey",
                 "dst_lag1h", "dst_lag3h", "dst_lag6h", "dst_lag12h", "dst_lag24h",
                 "dst_d1h", "dst_d6h",
                 "dst_mean3h", "dst_min3h", "dst_mean6h", "dst_min6h",
                 "dst_mean12h", "dst_min12h", "dst_mean24h", "dst_min24h"]
    feat_base = [c for c in feat_base if c in df.columns]
    for w in (3, 6, 12):
        roll = df[feat_base].rolling(window=w, min_periods=max(1, w // 2))
        df[[f"{c}_mean{w}h" for c in feat_base]] = roll.mean().values
        df[[f"{c}_min{w}h" for c in feat_base]] = roll.min().values
        df[[f"{c}_max{w}h" for c in feat_base]] = roll.max().values
    # Targets: Kyoto Dst at +1h / +6h, and storm-min over next 6h (t+1..t+6)
    df["dst_t1h"] = df["dst_kyoto"].shift(-1)
    df["dst_t6h"] = df["dst_kyoto"].shift(-6)
    df["dst_nextmin6h"] = df["dst_kyoto"].shift(-6).rolling(6, min_periods=6).min().values
    return df


def main():
    os.makedirs(PROC, exist_ok=True)
    print("loading OMNI2...")
    omni = load_omni()
    print(f"  OMNI rows: {len(omni)}, span {omni.Time.min()}..{omni.Time.max()}")
    print("loading Kyoto Dst...")
    dst = load_kyoto_dst()
    print(f"  Dst rows: {len(dst)}, span {dst.Time.min()}..{dst.Time.max()}")
    df = omni.merge(dst, on="Time", how="left")
    print("engineering features...")
    df = add_features(df)
    # keep rows where target exists and core drivers present
    core = ["BZ_GSM1800", "V1800", "N1800"]
    df = df.dropna(subset=["dst_t1h"]).reset_index(drop=True)
    df["cov_core"] = df[core].notna().mean(axis=1)
    out = os.path.join(PROC, "dataset.parquet")
    df.to_parquet(out, index=False)
    feats = [c for c in df.columns if c not in ("Time",)]
    pd.DataFrame({"feature": feats}).to_csv(os.path.join(PROC, "feature_dictionary.csv"), index=False)
    print(f"wrote {out}: {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"storm hours (dst<=-50): {(df['dst_kyoto'] <= -50).sum()}, "
          f"intense (<=-100): {(df['dst_kyoto'] <= -100).sum()}")


if __name__ == "__main__":
    main()
