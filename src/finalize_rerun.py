"""Finalize checkpointed training and plots as one result generation."""
import itertools
import json
from pathlib import Path
import joblib
import train
import evaluate
from rerun_integrity import (configuration, fingerprint, publish_generation,
                             validate, validate_set)


def main():
    original_results = Path(train.RES)
    digest, details = fingerprint(train.BASE, configuration(train))
    checkpoint = original_results / 'rerun-checkpoints' / digest
    names = [f'ridge_a{a}' for a in train.RIDGE_GRID['alpha']]
    keys = list(train.GBM_GRID)
    for vals in itertools.product(*[train.GBM_GRID[k] for k in keys]):
        kw = dict(zip(keys, vals))
        names.append(f"gbm_{kw['max_iter']}it_lr{kw['learning_rate']}_leaf{kw['max_leaf_nodes']}")
    selected = {}
    for target in train.REG_TARGETS:
        records = [json.loads(p.read_text()) for p in checkpoint.glob(target + '-*.json')]
        validate_set(records, names)
        for record in records:
            validate(record, digest, target, record['name'],
                     checkpoint / f"{target}-{record['name']}.joblib")
        records.sort(key=lambda r: names.index(r['name']))
        best = min(records, key=lambda r: r['val_rmse'])
        selected[target] = best
    targets = iter(train.REG_TARGETS)

    def cached_tune(Xtr, ytr, Xva, yva):
        target = next(targets)
        best = selected[target]
        return (best['name'], joblib.load(checkpoint / f"{target}-{best['name']}.joblib"),
                best['val_rmse'])

    expected = ['best_dst_t1h.joblib', 'best_dst_t6h.joblib', 'feature_cols.joblib',
                'clf_storm50_6h.joblib', 'clf_storm100_6h.joblib', 'metrics.json',
                'eval_summary.json', 'residuals_t6h.png', 'case_2015-03-17_st-patricks.png',
                'case_2017-09-08_sep2017.png', 'case_2024-05-11_gannon.png',
                'run-fingerprint.json']
    old_tune, old_eval_results = train.tune_regressor, evaluate.RES

    def produce(stage):
        train.RES = str(stage)
        train.tune_regressor = cached_tune
        evaluate.RES = str(stage)
        train.main()
        evaluate.main()
        (stage / 'run-fingerprint.json').write_text(json.dumps(details, indent=2) + '\n')

    try:
        generation = publish_generation(original_results, produce, expected)
        print('Completed immutable generation:', generation)
        print('Current results:', original_results / 'finalized')
    finally:
        train.RES = str(original_results)
        train.tune_regressor = old_tune
        evaluate.RES = old_eval_results


if __name__ == '__main__':
    main()
