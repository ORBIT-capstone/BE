from pathlib import Path

import pandas as pd

_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "active_income_stats.csv"
_stats: pd.DataFrame | None = None


def ensure_data_available() -> None:
    """/api/employees/simulate에 필요한 소득 통계 CSV의 존재를 앱 기동 시점에 검증한다.

    파일이 없으면 첫 요청에서 500이 나는 대신, 여기서 즉시 RuntimeError로 기동을 실패시킨다.
    """
    if not _CSV_PATH.exists():
        raise RuntimeError(
            f"필수 데이터 파일이 없습니다: {_CSV_PATH}\n"
            "재직자 연금 시뮬레이션(/api/employees/simulate)에 필요한 소득 통계 파일(active_income_stats.csv)입니다. "
            "scripts/preprocess.py로 생성하거나, 배포 환경에서 데이터 볼륨이 올바르게 마운트됐는지 확인하세요."
        )


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
