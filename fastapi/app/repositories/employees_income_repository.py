from pathlib import Path

import pandas as pd

_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "active_income_stats.csv"
_stats: pd.DataFrame | None = None


def _get_stats() -> pd.DataFrame:
    global _stats
    if _stats is None:
        _stats = pd.read_csv(_CSV_PATH)

        required_columns = {"구간", "평균"}
        missing_columns = required_columns - set(_stats.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV 필수 컬럼이 없습니다: {missing}")

    return _stats


def get_band_mean(band: str) -> float:
    df = _get_stats()
    row = df[df["구간"] == band]
    if row.empty:
        raise ValueError(f"구간 '{band}' 데이터가 없습니다.")
    return float(row.iloc[0]["평균"])
