"""Small offline tests, no training/network calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rerun_integrity import (IntegrityError, completed_results, fingerprint,
                             publish_generation, save_checkpoint, validate,
                             validate_set)


def test_configuration_source_and_dependency_changes_invalidate():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'src').mkdir()
        (root / 'data/processed').mkdir(parents=True)
        for name in ['train.py', 'build_dataset.py', 'download.py', 'evaluate.py',
                     'rerun_checkpointed.py', 'finalize_rerun.py', 'rerun_integrity.py']:
            (root / 'src' / name).write_text('original')
        (root / 'requirements.txt').write_text('requirements')
        (root / 'data/processed/dataset.parquet').write_bytes(b'data')
        with patch('rerun_integrity.importlib.metadata.version', return_value='1'):
            first, _ = fingerprint(root, {'seed': 0})
            changed_config, _ = fingerprint(root, {'seed': 1})
            assert first != changed_config
            (root / 'src/train.py').write_text('changed')
            changed_source, _ = fingerprint(root, {'seed': 0})
            assert first != changed_source
            (root / 'src/train.py').write_text('original')
        with patch('rerun_integrity.importlib.metadata.version', return_value='2'):
            changed_dep, _ = fingerprint(root, {'seed': 0})
            assert first != changed_dep


def test_checkpoint_requires_fingerprint_score_identity_and_model_hash(tmp_path):
    model = tmp_path / 'model'
    model.write_bytes(b'model')
    record = {'fingerprint': 'expected', 'target': 'dst', 'name': 'candidate',
              'val_rmse': 2.0, 'model_sha256': hashlib.sha256(b'model').hexdigest()}
    validate(record, 'expected', 'dst', 'candidate', model)
    for field, value in [('fingerprint', 'old'), ('target', 'other'),
                         ('name', 'other'), ('val_rmse', float('nan')),
                         ('model_sha256', 'bad')]:
        with pytest.raises(IntegrityError):
            validate(dict(record, **{field: value}), 'expected', 'dst', 'candidate', model)
    with pytest.raises(IntegrityError):
        validate_set([{'name': 'a'}, {'name': 'a'}], ['a', 'b'])


def test_optimized_python_still_rejects_invalid_checkpoints():
    source = "from rerun_integrity import validate_set; validate_set([], ['required'])"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    result = subprocess.run([sys.executable, '-O', '-c', source], env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'IntegrityError' in result.stderr


def test_checkpoint_record_published_only_after_model(tmp_path):
    record, model = tmp_path / 'record.json', tmp_path / 'model'
    def dump_failure(value, path):
        Path(path).write_bytes(b'partial')
        raise RuntimeError('interrupted')
    with pytest.raises(RuntimeError):
        save_checkpoint(record, model, None, {}, dump_failure)
    assert not record.exists()
    def dump(value, path):
        Path(path).write_bytes(b'complete')
    save_checkpoint(record, model, None, {'fingerprint': 'x'}, dump)
    assert json.loads(record.read_text())['model_sha256'] == hashlib.sha256(b'complete').hexdigest()


def test_failed_finalization_keeps_old_generation(tmp_path):
    def old(stage):
        (stage / 'model').write_text('old')
        (stage / 'metrics').write_text('old')
    initial = publish_generation(tmp_path, old, ['model', 'metrics'])
    def interrupted(stage):
        (stage / 'model').write_text('new')
        raise RuntimeError('interrupted')
    with pytest.raises(RuntimeError):
        publish_generation(tmp_path, interrupted, ['model', 'metrics'])
    assert completed_results(tmp_path) == initial
    assert (completed_results(tmp_path) / 'model').read_text() == 'old'
    assert not list((tmp_path / 'generations').glob('.staging-*'))


def test_incomplete_finalization_fails_and_complete_swap_keeps_reader_snapshot(tmp_path):
    with pytest.raises(IntegrityError):
        publish_generation(tmp_path, lambda stage: None, ['required'])
    assert not (tmp_path / 'finalized').exists()
    def produce(text):
        return lambda stage: (stage / 'required').write_text(text)
    old = publish_generation(tmp_path, produce('old'), ['required'])
    snapshot = completed_results(tmp_path)
    new = publish_generation(tmp_path, produce('new'), ['required'])
    assert completed_results(tmp_path) == new
    assert snapshot == old
    assert (snapshot / 'required').read_text() == 'old'
    (new / 'required').write_text('tampered')
    with pytest.raises(IntegrityError):
        completed_results(tmp_path)


def test_evaluation_does_not_rewrite_completed_generation(tmp_path, monkeypatch):
    import evaluate
    generation = publish_generation(tmp_path, lambda stage: (stage / 'required').write_text('done'), ['required'])
    monkeypatch.setattr(evaluate, 'RES', str(tmp_path))
    with patch.object(evaluate.pd, 'read_parquet', side_effect=AssertionError('must not rerun')):
        evaluate.main()
    assert completed_results(tmp_path) == generation
