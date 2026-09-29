"""Train Dst forecast models.

Time-based split (no shuffling across time):
  train 2015-2018 | val 2019 | test 2020 (final Dst) | extra 2021-2025 (provisional)

Regression: persistence, Ridge, HistGradientBoostingRegressor for Dst(+1h, +6h).
Classification: HistGradientBoostingClassifier for storm events defined as
  min Dst over the next 6h <= -50 / -100 nT (targets dst_nextmin6h).

Iteration 2 (rework pass): hyperparameter selection on the validation split,
leakage audit (dst_nextmin6h must never be a feature), dedicated storm-event
classifiers instead of thresholding point forecasts.

Saves models + metrics JSON to results/.
"""
import itertools
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROC = os.path.join(BASE, "data", "processed")
RES = os.path.join(BASE, "results")

REG_TARGETS = ["dst_t1h", "dst_t6h"]
CLS_TASKS = {"storm50_6h": ("dst_nextmin6h", -50.0),
             "storm100_6h": ("dst_nextmin6h", -100.0)}

RIDGE_GRID = {"alpha": [0.1, 1.0, 10.0, 100.0]}
GBM_GRID = {"max_iter": [100, 200, 400], "learning_rate": [0.05, 0.1],
            "max_leaf_nodes": [15, 31, 63]}


def rmse(a, b):
    return float(np.sqrt(mean_squared_error(a, b)))


def hour_skill(y_true_bin, y_pred_bin):
    """Hour-level detection skill. y_* are 0/1 arrays."""
    yt = np.asarray(y_true_bin).astype(int)
    yp = np.asarray(y_pred_bin).astype(int)
    tp = int(((yt == 1) & (yp == 1)).sum())
    fp = int(((yt == 0) & (yp == 1)).sum())
    fn = int(((yt == 1) & (yp == 0)).sum())
    pod = tp / (tp + fn) if (tp + fn) else None
    far = fp / (tp + fp) if (tp + fp) else None
    csi = tp / (tp + fp + fn) if (tp + fp + fn) else None
    rnd = lambda x: round(x, 3) if x is not None else None
    return {"n_pos_hours": int(yt.sum()), "POD": rnd(pod),
            "FAR": rnd(far), "CSI": rnd(csi),
            "TP": tp, "FP": fp, "FN": fn}


def tune_regressor(Xtr, ytr, Xva, yva):
    """Grid search on validation RMSE. Returns (name, fitted_model, val_rmse)."""
    best = (None, None, np.inf)
    for alpha in RIDGE_GRID["alpha"]:
        m = Ridge(alpha=alpha).fit(Xtr, ytr)
        r = rmse(yva, m.predict(Xva))
        if r < best[2]:
            best = (f"ridge_a{alpha}", m, r)
    keys = list(GBM_GRID)
    for vals in itertools.product(*[GBM_GRID[k] for k in keys]):
        kw = dict(zip(keys, vals))
        m = HistGradientBoostingRegressor(random_state=0, **kw).fit(Xtr, ytr)
        r = rmse(yva, m.predict(Xva))
        if r < best[2]:
            best = (f"gbm_{kw['max_iter']}it_lr{kw['learning_rate']}_leaf{kw['max_leaf_nodes']}", m, r)
    return best


def main():
    os.makedirs(RES, exist_ok=True)
    df = pd.read_parquet(os.path.join(PROC, "dataset.parquet"))
    # Leakage audit: dst_nextmin6h is built from FUTURE Dst -> never a feature.
    leak = [c for c in df.columns if "nextmin" in c]
    feat_cols = [c for c in df.columns if c not in
                 ("Time", "dst_kyoto", "dst_t1h", "dst_t6h", "dst_min6h",
                  "dst_nextmin6h", "DST1800", "KP1800", "cov_core")]
    assert not any(c in feat_cols for c in leak), f"LEAK: {leak}"
    assert "dst_nextmin6h" not in feat_cols
    df = df.dropna(subset=feat_cols).reset_index(drop=True)
    print(f"modeling rows: {len(df)}, features: {len(feat_cols)}, leaked cols blocked: {leak}")

    splits = {
        "train": ("2015-01-01", "2019-01-01"),
        "val": ("2019-01-01", "2020-01-01"),
        "test": ("2020-01-01", "2021-01-01"),
        "extra": ("2021-01-01", "2025-01-01"),
    }
    parts = {k: df[(df.Time >= s) & (df.Time < e)].reset_index(drop=True)
             for k, (s, e) in splits.items()}
    for k, p in parts.items():
        print(f"  {k}: {len(p)} rows")

    Xtr = parts["train"][feat_cols].values
    Xva = parts["val"][feat_cols].values
    metrics = {}

    # ---- regression ----
    for tgt in REG_TARGETS:
        ytr, yva = parts["train"][tgt].values, parts["val"][tgt].values
        name, model, val_rmse = tune_regressor(Xtr, ytr, Xva, yva)
        print(f"{tgt}: best={name} val_RMSE={val_rmse:.2f}")
        joblib.dump(model, os.path.join(RES, f"best_{tgt}.joblib"))
        m = {"best_model": name, "val_rmse_best": round(val_rmse, 2)}
        for split in ("val", "test", "extra"):
            p = parts[split]
            X, y = p[feat_cols].values, p[tgt].values
            persist = p["dst_kyoto"].values
            sm = {"n": len(p),
                  "persistence": {"RMSE": round(rmse(y, persist), 2),
                                  "MAE": round(mean_absolute_error(y, persist), 2)},
                  "model": {"RMSE": round(rmse(y, model.predict(X)), 2),
                            "MAE": round(mean_absolute_error(y, model.predict(X)), 2)}}
            m[split] = sm
        # feature importance: permutation importance on a val subset (model-agnostic)
        from sklearn.inspection import permutation_importance
        rng = np.random.RandomState(0)
        sub = rng.choice(len(Xva), size=min(2000, len(Xva)), replace=False)
        pi = permutation_importance(model, Xva[sub], yva[sub], n_repeats=3,
                                    scoring="neg_root_mean_squared_error",
                                    random_state=0)
        order = np.argsort(pi.importances_mean)[::-1][:15]
        m["top_features"] = [(feat_cols[i], round(float(pi.importances_mean[i]), 4))
                             for i in order]
        metrics[tgt] = m
    joblib.dump(feat_cols, os.path.join(RES, "feature_cols.joblib"))

    # ---- storm-event classification ----
    for task, (src, thr) in CLS_TASKS.items():
        y_all = {}
        for k, p in parts.items():
            y_all[k] = (p[src].values <= thr).astype(int)
        print(f"{task}: train positives={y_all['train'].sum()}/{len(y_all['train'])}")
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
                                             max_leaf_nodes=31, class_weight="balanced",
                                             random_state=0)
        clf.fit(Xtr, y_all["train"])
        joblib.dump(clf, os.path.join(RES, f"clf_{task}.joblib"))
        tm = {}
        for split in ("val", "test", "extra"):
            p = parts[split]
            proba = clf.predict_proba(p[feat_cols].values)[:, 1]
            tm[f"{split}_cut0.5"] = hour_skill(y_all[split], proba >= 0.5)
            if split == "test":
                tm["test_operating_points"] = {
                    str(c): hour_skill(y_all[split], proba >= c)
                    for c in (0.3, 0.5, 0.7)}
        metrics[task] = tm

    with open(os.path.join(RES, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("wrote", os.path.join(RES, "metrics.json"))


if __name__ == "__main__":
    main()
