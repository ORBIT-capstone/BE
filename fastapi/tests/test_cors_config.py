"""CORS 설정이 CORS_ALLOWED_ORIGINS 환경변수 기반으로 동작하는지에 대한 회귀 테스트."""

import pytest
from fastapi.testclient import TestClient

from app.config.cors import get_cors_allowed_origins


def test_defaults_to_local_origin_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    assert get_cors_allowed_origins() == ["http://localhost:5173"]


def test_parses_comma_separated_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,https://orbit-zeta-liard.vercel.app",
    )

    assert get_cors_allowed_origins() == [
        "http://localhost:5173",
        "https://orbit-zeta-liard.vercel.app",
    ]


def test_strips_whitespace_around_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        " http://localhost:5173 , https://orbit-zeta-liard.vercel.app ",
    )

    assert get_cors_allowed_origins() == [
        "http://localhost:5173",
        "https://orbit-zeta-liard.vercel.app",
    ]


def test_falls_back_to_default_when_env_var_is_blank(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "  , ,")

    assert get_cors_allowed_origins() == ["http://localhost:5173"]


def test_never_resolves_to_wildcard_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    assert "*" not in get_cors_allowed_origins()


def test_app_sends_cors_headers_for_configured_origin():
    from app.main import app

    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_app_rejects_cors_for_unconfigured_origin():
    from app.main import app

    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers


def test_app_does_not_use_wildcard_middleware_config():
    from app.main import app
    from fastapi.middleware.cors import CORSMiddleware

    cors_middleware = next(
        m for m in app.user_middleware if m.cls is CORSMiddleware
    )
    assert "*" not in cors_middleware.kwargs["allow_origins"]
    assert cors_middleware.kwargs["allow_credentials"] is True
