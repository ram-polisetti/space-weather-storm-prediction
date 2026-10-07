"""Evaluate the final models: regression error, storm-event skill, case studies.

Loads models from results/ (written by train.py). Writes PNGs + a JSON summary
to results/. Case studies: 2015-03-17 (St Patrick's), 2017-09-08 (Sep 2017),
2024-05-11 (Gannon superstorm).
"""
import json
import os
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from rerun_integrity import completed_results

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROC = os.path.join(BASE, "data", "processed")
RES = os.path.join(BASE, "results")

CASES = {
    "2015-03-17_st-patricks": ("2015-03-15", "2015-03-20"),
    "2017-09-08_sep2017": ("2017-09-06", "2017-09-11"),
    "2024-05-11_gannon": ("2024-05-09", "2024-05-14"),
}


def main():
    resolved = completed_results(RES)
    if resolved != Path(RES):
        print('Completed generation already contains plots:', resolved)
        return
    os.makedirs(RES, exist_ok=True)
    df = pd.read_parquet(os.path.join(PROC, "dataset.parquet"))
    feats = joblib.load(os.path.join(RES, "feature_cols.joblib"))
    reg = joblib.load(os.path.join(RES, "best_dst_t6h.joblib"))
    clf = joblib.load(os.path.join(RES, "clf_storm50_6h.joblib"))
    d = df.dropna(subset=feats + ["dst_t6h", "dst_nextmin6h"]).reset_index(drop=True)
    X = d[feats].values
    d["pred_t6h"] = reg.predict(X)
    d["storm50_proba"] = clf.predict_proba(X)[:, 1]

    resid = d["dst_t6h"].values - d["pred_t6h"].values
    summary = {
        "n": len(d),
        "resid_mean": round(float(resid.mean()), 3),
        "resid_std": round(float(resid.std()), 3),
        "resid_p1": round(float(np.percentile(resid, 1)), 2),
        "resid_p99": round(float(np.percentile(resid, 99)), 2),
    }

    # residual histogram
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(resid, bins=120, range=(-60, 60))
    ax.set_xlabel("residual (true - predicted) Dst@+6h [nT]")
    ax.set_ylabel("hours")
    ax.set_title("Residual distribution, +6h Dst model (all years)")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "residuals_t6h.png"), dpi=110)
    plt.close(fig)

    # case studies
    for name, (s, e) in CASES.items():
        sub = d[(d.Time >= s) & (d.Time < e)].copy()
        if len(sub) == 0:
            continue
        fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        t = sub["Time"]
        axes[0].plot(t, sub["BZ_GSM1800"], label="Bz GSM")
        axes[0].plot(t, sub["V1800"] / 100, label="V/100 [km/s /100]")
        axes[0].legend(loc="best", fontsize=8)
        axes[0].set_ylabel("solar wind")
        axes[0].set_title(f"{name}: drivers")
        axes[1].plot(t, sub["dst_kyoto"], label="Kyoto Dst (obs)")
        axes[1].axhline(-50, color="orange", ls="--", lw=1, label="storm thr")
        axes[1].axhline(-100, color="red", ls="--", lw=1)
        axes[1].legend(loc="best", fontsize=8)
        axes[1].set_ylabel("Dst [nT]")
        axes[1].set_title("observed Dst")
        axes[2].plot(t, sub["dst_t6h"], label="true Dst@+6h")
        axes[2].plot(t, sub["pred_t6h"], label="model Dst@+6h", alpha=0.8)
        ax2 = axes[2].twinx()
        ax2.fill_between(t, 0, sub["storm50_proba"], color="red", alpha=0.25,
                         label="P(storm in 6h)")
        axes[2].legend(loc="upper left", fontsize=8)
        ax2.legend(loc="upper right", fontsize=8)
        axes[2].set_ylabel("Dst@+6h [nT]")
        axes[2].set_title("+6h forecast vs truth; storm-event probability")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(os.path.join(RES, f"case_{name}.png"), dpi=110)
        plt.close(fig)
        summary[name] = {
            "min_dst_obs": round(float(sub["dst_kyoto"].min()), 1),
            "min_pred_t6h": round(float(sub["pred_t6h"].min()), 1),
            "max_storm_proba": round(float(sub["storm50_proba"].max()), 3),
        }
        print(name, summary[name])

    with open(os.path.join(RES, "eval_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("wrote eval outputs to", RES)


if __name__ == "__main__":
    main()
