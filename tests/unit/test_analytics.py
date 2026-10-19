"""
Unit tests for LogShield Data Analytics Studio & Profiling Engine
"""

import pytest
from fastapi.testclient import TestClient

from src.logshield.analytics import DatasetAnalyzer
from src.logshield.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def analyzer():
    return DatasetAnalyzer()


def test_dataset_discovery(analyzer):
    datasets = analyzer.discover_datasets()
    assert isinstance(datasets, list)
    assert len(datasets) >= 5
    ids = [d.id for d in datasets]
    assert "hourly_404_errors" in ids
    assert "status_code_breakdown" in ids
    assert "top_404_paths" in ids


def test_profile_hourly_errors(analyzer):
    profile = analyzer.profile_dataset("hourly_404_errors")
    assert profile.dataset_id == "hourly_404_errors"
    assert profile.total_rows == 24
    assert profile.total_columns == 2
    assert profile.duplicate_rows == 0
    assert profile.quality_score == 100.0

    col_names = [c.name for c in profile.columns]
    assert "hour" in col_names
    assert "error_count" in col_names

    err_col = next(c for c in profile.columns if c.name == "error_count")
    assert err_col.dtype == "numeric"
    assert err_col.min_val == 463.0
    assert err_col.max_val == 4655.0
    assert err_col.mean is not None
    assert err_col.median is not None


def test_profile_status_code_breakdown(analyzer):
    profile = analyzer.profile_dataset("status_code_breakdown")
    assert profile.total_rows == 5
    assert profile.quality_score == 100.0
    status_col = next(c for c in profile.columns if c.name == "status")
    assert status_col.total_count == 5
    assert status_col.null_count == 0


def test_path_traversal_protection(analyzer):
    with pytest.raises(ValueError, match="Path traversal"):
        analyzer.profile_dataset("../../../etc/passwd")


def test_in_memory_inspection_csv(analyzer):
    csv_data = "col1,col2,col3\n10,alpha,100\n20,,200\n30,gamma,300\n"
    profile = analyzer.inspect_in_memory(csv_data, format="csv", name="sample_test")
    assert profile.total_rows == 3
    assert profile.total_columns == 3

    col2 = next(c for c in profile.columns if c.name == "col2")
    assert col2.null_count == 1
    assert col2.null_percentage > 0


def test_in_memory_inspection_json(analyzer):
    json_data = '[{"host": "srv1", "latency": 12.5}, {"host": "srv2", "latency": 45.2}]'
    profile = analyzer.inspect_in_memory(json_data, format="json", name="latency_test")
    assert profile.total_rows == 2
    assert profile.total_columns == 2
    latency_col = next(c for c in profile.columns if c.name == "latency")
    assert latency_col.dtype == "numeric"
    assert latency_col.mean == pytest.approx(28.85, rel=1e-2)


def test_in_memory_empty_content_raises(analyzer):
    with pytest.raises(ValueError, match="empty"):
        analyzer.inspect_in_memory("")


def test_in_memory_malformed_csv_raises(analyzer):
    with pytest.raises(ValueError):
        analyzer.inspect_in_memory('a,b\n"unclosed_quote_field,123', format="csv")



def test_export_dataset_formats(analyzer):
    csv_out = analyzer.export_dataset("status_code_breakdown", format="csv")
    assert "status,count" in csv_out

    json_out = analyzer.export_dataset("status_code_breakdown", format="json")
    assert '"status": 200' in json_out

    md_out = analyzer.export_dataset("status_code_breakdown", format="markdown")
    assert "| status | count  |" in md_out
    assert "| 200    |" in md_out


def test_export_dataset_filter_and_sort(analyzer):
    out = analyzer.export_dataset(
        "top_404_paths",
        format="csv",
        filter_column="path",
        filter_value="admin",
        sort_column="hits",
        sort_descending=True
    )
    assert "/admin/login" in out


def test_api_list_datasets(client):
    res = client.get("/api/analytics/datasets")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5


def test_api_get_profile(client):
    res = client.get("/api/analytics/profile?dataset_id=status_code_breakdown")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "status_code_breakdown"
    assert data["quality_score"] == 100.0


def test_api_inspect_endpoint(client):
    res = client.post(
        "/api/analytics/inspect",
        json={"content": "x,y\n1,2\n3,4", "format": "csv", "name": "mini"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_rows"] == 2
    assert data["total_columns"] == 2


def test_api_export_endpoint(client):
    res = client.post(
        "/api/analytics/export",
        json={"dataset_id": "status_code_breakdown", "format": "markdown", "limit": 2}
    )
    assert res.status_code == 200
    assert "| status | count  |" in res.text


def test_in_memory_inspection_with_booleans_and_missing(analyzer):
    content = "user,attempts,success\nadmin,5,false\nroot,12,false\nuser1,1,true\nuser2,,false"
    profile = analyzer.inspect_in_memory(content, format="csv", name="auth_sample")
    assert profile.total_rows == 4
    assert profile.total_columns == 3

    success_col = next(c for c in profile.columns if c.name == "success")
    assert success_col.dtype == "boolean"

    attempts_col = next(c for c in profile.columns if c.name == "attempts")
    assert attempts_col.dtype == "numeric"
    assert attempts_col.null_count == 1

