"""Fail-closed checkpoints and atomic, immutable result generations."""
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import tempfile
import uuid
from pathlib import Path


class IntegrityError(RuntimeError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(base, configuration):
    base = Path(base)
    sources = ['train.py', 'build_dataset.py', 'download.py', 'evaluate.py',
               'rerun_checkpointed.py', 'finalize_rerun.py', 'rerun_integrity.py']
    dependencies = ['numpy', 'pandas', 'scikit-learn', 'scipy', 'joblib',
                    'pyarrow', 'matplotlib']
    details = {
        'schema': 1, 'python': platform.python_version(),
        'dependencies': {name: importlib.metadata.version(name) for name in dependencies},
        'sources': {name: sha256(base / 'src' / name) for name in sources},
        'requirements_sha256': sha256(base / 'requirements.txt'),
        'dataset_sha256': sha256(base / 'data/processed/dataset.parquet'),
        'configuration': configuration,
    }
    digest = hashlib.sha256(json.dumps(details, sort_keys=True).encode()).hexdigest()
    return digest, details


def configuration(train):
    return {'reg_targets': train.REG_TARGETS, 'classifiers': train.CLS_TASKS,
            'ridge_grid': train.RIDGE_GRID, 'gbm_grid': train.GBM_GRID,
            'seed': 0,
            'splits': {'train': ['2015-01-01', '2019-01-01'],
                       'val': ['2019-01-01', '2020-01-01'],
                       'test': ['2020-01-01', '2021-01-01'],
                       'extra': ['2021-01-01', '2025-01-01']}}


def validate(record, expected, target, name, model_path):
    if record.get('fingerprint') != expected:
        raise IntegrityError('checkpoint fingerprint missing or stale; use a fresh checkpoint directory')
    if record.get('target') != target or record.get('name') != name:
        raise IntegrityError('checkpoint target or candidate differs')
    score = record.get('val_rmse')
    if not isinstance(score, (float, int)) or not math.isfinite(score) or score < 0:
        raise IntegrityError('invalid validation score')
    if not Path(model_path).is_file() or record.get('model_sha256') != sha256(model_path):
        raise IntegrityError('checkpoint model missing or hash differs')


def validate_set(records, names):
    if sorted(r.get('name', '') for r in records) != sorted(names):
        raise IntegrityError('checkpoint candidate set incomplete or duplicated')


def save_checkpoint(path, model_path, model, record, dump):
    # Model is complete before JSON advertises a usable checkpoint.
    path, model_path = Path(path), Path(model_path)
    temp_model = model_path.with_suffix('.tmp')
    dump(model, temp_model)
    os.replace(temp_model, model_path)
    record = dict(record, model_sha256=sha256(model_path))
    temp_record = path.with_suffix('.tmp')
    temp_record.write_text(json.dumps(record, sort_keys=True) + '\n')
    os.replace(temp_record, path)


def publish_generation(results, producer, expected_files):
    """Readers follow one pointer; a failed producer never changes it.

    POSIX local-filesystem atomic rename protects concurrent readers, not
    power-loss durability. Do not use shared/network filesystems. Never
    overwrite an already published generation or remove old generations.
    """
    results = Path(results)
    generations = results / 'generations'
    generations.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=generations))
    pointer = results / 'finalized'
    temporary_pointer = results / ('.finalized-' + uuid.uuid4().hex)
    try:
        producer(stage)
        missing = [name for name in expected_files if not (stage / name).is_file()]
        if missing:
            raise IntegrityError('finalization incomplete: ' + ', '.join(missing))
        hashes = {name: sha256(stage / name) for name in expected_files}
        (stage / 'COMPLETED.json').write_text(json.dumps({'hashes': hashes}, sort_keys=True) + '\n')
        generation = generations / uuid.uuid4().hex
        os.replace(stage, generation)
        os.symlink(os.path.relpath(generation, results), temporary_pointer)
        os.replace(temporary_pointer, pointer)
        return generation
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if temporary_pointer.is_symlink():
            temporary_pointer.unlink()


def completed_results(results):
    """Resolve once so a pointer swap cannot mix model generations."""
    pointer = Path(results) / 'finalized'
    if not pointer.is_symlink():
        return Path(results)  # original non-checkpoint train.py workflow
    generation = pointer.resolve(strict=True)
    record = json.loads((generation / 'COMPLETED.json').read_text())
    for name, digest in record['hashes'].items():
        if sha256(generation / name) != digest:
            raise IntegrityError('published generation hash mismatch: ' + name)
    return generation
