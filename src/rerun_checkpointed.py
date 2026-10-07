"""Same training grid and selection as train.py, one resumable work unit.

Usage: python src/rerun_checkpointed.py
No changed data/splits/grid; checkpoints avoid foreground timeouts.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import train
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import Ridge

base = Path(train.BASE)
checkpoint = base / 'results' / 'rerun-checkpoints'
checkpoint.mkdir(exist_ok=True)
data_path = base / 'data' / 'processed' / 'dataset.parquet'
source_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
df = pd.read_parquet(data_path)
feat = [c for c in df.columns if c not in ('Time','dst_kyoto','dst_t1h','dst_t6h','dst_min6h','dst_nextmin6h','DST1800','KP1800','cov_core')]
assert not any('nextmin' in c for c in feat)
df = df.dropna(subset=feat).reset_index(drop=True)
parts = train.split_dataset(df, {'train':('2015-01-01','2019-01-01'),'val':('2019-01-01','2020-01-01'),'test':('2020-01-01','2021-01-01'),'extra':('2021-01-01','2025-01-01')})
Xtr=parts['train'][feat].values;Xva=parts['val'][feat].values
jobs=[]
for target in train.REG_TARGETS:
 for alpha in train.RIDGE_GRID['alpha']:
  jobs.append((target,f'ridge_a{alpha}',Ridge(alpha=alpha)))
 keys=list(train.GBM_GRID)
 for vals in itertools.product(*[train.GBM_GRID[k] for k in keys]):
  kw=dict(zip(keys,vals));jobs.append((target,f"gbm_{kw['max_iter']}it_lr{kw['learning_rate']}_leaf{kw['max_leaf_nodes']}",HistGradientBoostingRegressor(random_state=0,**kw)))
for target,name,model in jobs:
 record=checkpoint/f'{target}-{name}.json'
 if record.exists():
  assert json.loads(record.read_text())['dataset_sha256']==source_hash
  continue
 model.fit(Xtr,parts['train'][target].values)
 score=train.rmse(parts['val'][target].values,model.predict(Xva))
 joblib.dump(model,checkpoint/f'{target}-{name}.joblib')
 record.write_text(json.dumps({'target':target,'name':name,'val_rmse':score,'dataset_sha256':source_hash})+'\n')
 print(json.dumps({'completed':name,'target':target,'val_rmse':score}),flush=True)
 break
else:
 print('All regression candidates complete; final selection/evaluation still required',flush=True)
