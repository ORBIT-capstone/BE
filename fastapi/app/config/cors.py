"""CORS origin configuration for the FastAPI application."""

import os

CORS_ALLOWED_ORIGINS_ENV_VAR = "CORS_ALLOWED_ORIGINS"
_DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173"]


def get_cors_allowed_origins() -> list[str]:
    """Parse CORS_ALLOWED_ORIGINS (comma-separated) into a list of origins.

    Falls back to the local dev origin when the env var is unset or empty,
    so this must never resolve to a wildcard: allow_credentials=True is
    incompatible with "*" in allow_origins.
    """
    raw = os.environ.get(CORS_ALLOWED_ORIGINS_ENV_VAR)
    if raw is None:
        return list(_DEFAULT_ALLOWED_ORIGINS)

    origins = [
        origin.strip()
        for origin in raw.split(",")
        if origin.strip() and origin.strip() != "*"
    ]
    return origins if origins else list(_DEFAULT_ALLOWED_ORIGINS)
