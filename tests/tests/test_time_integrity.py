"""Regression checks using actual NASA/Kyoto records, not generated data."""
from pathlib import Path
import pandas as pd
import pytest
from src import build_dataset as build
from src.train import split_dataset

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture
def observations(monkeypatch, tmp_path):
    (tmp_path / "dst_kyoto").mkdir()
    for source in FIXTURES.glob("*.csv"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    source = FIXTURES / "dst_provisional_202405.txt"
    (tmp_path / "dst_kyoto" / source.name).write_bytes(source.read_bytes())
    monkeypatch.setattr(build, "RAW", str(tmp_path))
    return build.load_omni().merge(build.load_kyoto_dst(), on="Time", how="left")

def test_real_storm_and_fill_values(observations):
    assert len(observations) == 168
    assert observations.dst_kyoto.min() == -406
    assert observations.V1800.isna().sum() == 1
    assert observations.V1800.max() < 9999

def test_targets_match_exact_utc_hours(observations):
    result = build.add_features(observations)
    dst = observations.set_index("Time").dst_kyoto
    for row in result.iloc[:-6].itertuples():
        assert row.dst_t1h == dst.loc[row.Time + pd.Timedelta(hours=1)]
        assert row.dst_t6h == dst.loc[row.Time + pd.Timedelta(hours=6)]
        expected = dst.loc[row.Time + pd.Timedelta(hours=1):row.Time + pd.Timedelta(hours=6)].min()
        assert row.dst_nextmin6h == expected

def test_missing_hour_is_not_next_row(observations):
    missing_time = observations.Time.iloc[30]
    result = build.add_features(observations.drop(index=30)).set_index("Time")
    assert len(result) == len(observations)
    assert pd.isna(result.loc[missing_time, "dst_kyoto"])
    assert pd.isna(result.loc[missing_time - pd.Timedelta(hours=1), "dst_t1h"])
    assert pd.isna(result.loc[missing_time - pd.Timedelta(hours=6), "dst_t6h"])
    assert pd.isna(result.loc[missing_time - pd.Timedelta(hours=3), "dst_nextmin6h"])
    assert pd.isna(result.loc[missing_time + pd.Timedelta(hours=1), "dst_lag1h"])

def test_sorting_preserves_hourly_targets(observations):
    expected = build.add_features(observations)
    actual = build.add_features(observations.iloc[::-1])
    pd.testing.assert_frame_equal(actual, expected)

def test_duplicate_times_rejected(observations):
    with pytest.raises(ValueError, match="unique"):
        build.add_features(pd.concat([observations, observations.iloc[:1]]))

def test_split_purges_future_labels_and_unknowns(observations):
    result = build.add_features(observations)
    parts = split_dataset(result, {"train": ("2024-05-08", "2024-05-11"),
                                   "test": ("2024-05-11", "2024-05-15")})
    assert len(parts["train"]) == 66
    assert len(parts["test"]) == 90
    for name, end in [("train", "2024-05-11"), ("test", "2024-05-15")]:
        assert (parts[name].Time + pd.Timedelta(hours=6) < pd.Timestamp(end, tz="UTC")).all()
        assert parts[name][["dst_t1h", "dst_t6h", "dst_nextmin6h"]].notna().all().all()
    gap = build.add_features(observations.drop(index=30))
    cleaned = split_dataset(gap, {"all": ("2024-05-08", "2024-05-15")})["all"]
    assert cleaned.dst_nextmin6h.notna().all()
