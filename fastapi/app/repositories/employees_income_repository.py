from pathlib import Path

import pandas as pd

from app.exceptions import DataSourceError

_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "active_income_stats.csv"
_stats: pd.DataFrame | None = None
_stats_path: Path | None = None


def ensure_data_available() -> None:
    """필수 CSV를 읽고 컬럼까지 검증해 앱 기동 중 구성 오류를 발견한다."""
    _get_stats()


def _get_stats() -> pd.DataFrame:
    global _stats, _stats_path
    if _stats is None or _stats_path != _CSV_PATH:
        if not _CSV_PATH.exists():
            raise DataSourceError(
                f"필수 데이터 파일이 없습니다: {_CSV_PATH}\n"
                "재직자 연금 시뮬레이션(/api/employees/simulate)에 필요한 소득 통계 파일(active_income_stats.csv)입니다. "
                "scripts/preprocess.py로 생성하거나, 배포 환경에서 데이터 볼륨이 올바르게 마운트됐는지 확인하세요."
            )
        try:
            loaded_stats = pd.read_csv(_CSV_PATH)
        except Exception as exc:
            raise DataSourceError(f"소득 통계 CSV를 읽을 수 없습니다: {_CSV_PATH}") from exc

        missing_columns = {"구간", "평균"} - set(loaded_stats.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise DataSourceError(f"CSV 필수 컬럼이 없습니다: {missing}")

        _stats = loaded_stats
        _stats_path = _CSV_PATH

    return _stats


def get_band_mean(band: str) -> float:
    df = _get_stats()
    row = df[df["구간"] == band]
    if row.empty:
        raise DataSourceError(f"구간 '{band}' 데이터가 없습니다.")
    return float(row.iloc[0]["평균"])
