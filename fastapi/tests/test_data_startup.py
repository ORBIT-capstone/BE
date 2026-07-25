import pytest

from app.repositories import employees_income_repository


def test_ensure_data_available_passes_when_csv_exists():
    employees_income_repository.ensure_data_available()


def test_ensure_data_available_raises_clear_error_when_csv_missing(monkeypatch, tmp_path):
    missing_path = tmp_path / "active_income_stats.csv"
    monkeypatch.setattr(employees_income_repository, "_CSV_PATH", missing_path)

    with pytest.raises(RuntimeError) as exc_info:
        employees_income_repository.ensure_data_available()

    message = str(exc_info.value)
    assert str(missing_path) in message
    assert "active_income_stats.csv" in message


def test_app_startup_fails_fast_when_required_csv_missing(monkeypatch, tmp_path):
    """앱 기동 시점에 검증이 실행되어, 첫 요청이 아니라 startup에서 즉시 실패해야 한다."""
    from fastapi.testclient import TestClient

    from app.main import app

    missing_path = tmp_path / "active_income_stats.csv"
    monkeypatch.setattr(employees_income_repository, "_CSV_PATH", missing_path)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
