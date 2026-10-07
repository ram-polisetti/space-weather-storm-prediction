"""Finalize unchanged train.py using all checkpointed regression candidates."""
import hashlib
import json
from pathlib import Path
import joblib
import train

checkpoint = Path(train.RES) / 'rerun-checkpoints'
# Original train.main visits horizons in this order.
targets = iter(train.REG_TARGETS)
def cached_tune(Xtr, ytr, Xva, yva):
    target = next(targets)
    records = [json.loads(p.read_text()) for p in checkpoint.glob(target + '-*.json')]
    assert len(records) == 22, (target, len(records))
    source_hash = hashlib.sha256((Path(train.PROC) / 'dataset.parquet').read_bytes()).hexdigest()
    assert all(r['dataset_sha256'] == source_hash for r in records)
    # Stable original candidate order makes ties behave like train.py.
    import itertools
    names = [f'ridge_a{a}' for a in train.RIDGE_GRID['alpha']]
    keys=list(train.GBM_GRID)
    for vals in itertools.product(*[train.GBM_GRID[k] for k in keys]):
        kw=dict(zip(keys,vals))
        names.append(f"gbm_{kw['max_iter']}it_lr{kw['learning_rate']}_leaf{kw['max_leaf_nodes']}")
    assert sorted(r['name'] for r in records) == sorted(names)
    assert all(r['target'] == target for r in records)
    records.sort(key=lambda r:names.index(r['name']))
    best=min(records,key=lambda r:r['val_rmse'])
    return best['name'], joblib.load(checkpoint/f"{target}-{best['name']}.joblib"), best['val_rmse']
train.tune_regressor=cached_tune
train.main()
