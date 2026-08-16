"""재직월수를 법정 지급률 tranche(연도 구간)별 월수로 분해하고, Tier 1 잠정 비교모형
(확정된 연도별 지급률 tranche를 적용한 예측값)을 계산한다.

**Tier 1은 법정 산식이 아니다.** 보정률·소득재분배(A/B/C값)·2009년 이전 별도 산식
(평균보수월액 기반)·종전규정 유리 원칙(min)이 빠져 있다. 이 모듈은 "확정된 연도별
지급률 tranche를 적용했을 때 기존 baseline 대비 정합성이 얼마나 개선되는가"만 잰다.

또한 2009년 이전 재직기간의 법정 산정기초는 평균보수월액인데 이 데이터셋에는 없다.
Tier 1은 전 구간에 평균기준소득월액을 공통 proxy로 사용하는 잠정 비교모형이며,
2009년 이전 구간에는 입력소득 대체로 인한 구조적 오차가 포함된다.

tranche 구간은 -inf(2009년 이전)부터 +inf(2036년 이후 고정 요율)까지 빈틈없이
덮는다 — 어떤 재직기간 입력에 대해서도 sum(구간별 월수) == 재직월수 가 항상 성립한다
(2036년 이후 구간이 없던 이전 버전에서는 2026년 이후로 뻗는 재직기간의 월수가 조용히
소실됐었다 — tests/test_tranche.py의 무경계 회귀 테스트로 고정했다).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from tranche_rates import (  # noqa: E402
    PENSION_RATE_BY_YEAR,
    RATE_2010_2015,
    RATE_2036_PLUS,
    RATE_PRE_2010,
)

TRANCHE_YEARS = sorted(PENSION_RATE_BY_YEAR.keys())  # 2016..2035


def idx_from_yyyymm(yyyymm: pd.Series | int) -> pd.Series | int:
    """YYYYMM 정수를 절대월 인덱스로 변환: idx = year*12 + (month-1)."""
    year = yyyymm // 100
    month = yyyymm % 100
    return year * 12 + (month - 1)


def _idx(year: int, month: int) -> int:
    return year * 12 + (month - 1)


# 각 tranche의 [하한, 상한] 절대월 인덱스 (inclusive).
# pre_2010의 하한과 y2036_plus의 상한은 각각 -inf/+inf 대용 sentinel이다 —
# 구간 목록이 전체 정수축을 빈틈없이 덮으므로 어떤 입력이 와도 월수가 소실되지 않는다.
_NEG_INF_IDX = -10**9
_POS_INF_IDX = 10**9
_TRANCHE_IDX_RANGES: list[tuple[str, int, int]] = [
    ("pre_2010", _NEG_INF_IDX, _idx(2009, 12)),
    ("y2010_2015", _idx(2010, 1), _idx(2015, 12)),
]
for _y in TRANCHE_YEARS:
    _TRANCHE_IDX_RANGES.append((f"y{_y}", _idx(_y, 1), _idx(_y, 12)))
_TRANCHE_IDX_RANGES.append(("y2036_plus", _idx(2036, 1), _POS_INF_IDX))

TRANCHE_COLUMNS = [name for name, _, _ in _TRANCHE_IDX_RANGES]

_RATE_BY_TRANCHE: dict[str, float] = {"pre_2010": RATE_PRE_2010, "y2010_2015": RATE_2010_2015}
_RATE_BY_TRANCHE.update({f"y{y}": PENSION_RATE_BY_YEAR[y] for y in TRANCHE_YEARS})
_RATE_BY_TRANCHE["y2036_plus"] = RATE_2036_PLUS


def decompose_tranche_months(
    추정임용연월: pd.Series,
    재직월수: pd.Series,
    offset_months: int = 0,
) -> pd.DataFrame:
    """재직월수를 연도 구간별 월수로 분해한다.

    offset_months: 추정임용연월의 민감도 분석용 이동값(개월). 재직월수(구간 길이)는
    고정하고, 구간 시작점만 이동시킨다 — 재직월수는 데이터에 주어진 사실이고
    추정임용연월만 불확실하기 때문이다. tranche 구간이 -inf~+inf를 빈틈없이 덮으므로
    offset과 무관하게 항상 sum(구간별 월수) == 재직월수 가 성립한다
    (tests/test_tranche.py::test_decompose_never_loses_months 참조).

    반환: TRANCHE_COLUMNS를 컬럼으로 갖는 DataFrame (각 행 = 해당 tranche 월수, 정수).
    """
    start_idx = idx_from_yyyymm(추정임용연월) + offset_months
    end_idx = start_idx + 재직월수 - 1  # inclusive

    result: dict[str, pd.Series] = {}
    for name, t_lo, t_hi in _TRANCHE_IDX_RANGES:
        overlap_lo = np.maximum(start_idx, t_lo)
        overlap_hi = np.minimum(end_idx, t_hi)
        months = np.maximum(0, overlap_hi - overlap_lo + 1)
        result[name] = months

    return pd.DataFrame(result, index=재직월수.index)


def legal_rate_sum(tranche_months: pd.DataFrame) -> pd.Series:
    """tranche 월수 분해 결과에 연도별 법정 요율을 적용한 가중합(단위: 무차원 비율의 합).

    predict_tier1()의 핵심 계산을 분리해 재사용 가능하게 한다 —
    예측 연금월액 = 평균기준소득월액 x legal_rate_sum(...).
    """
    rate_sum = pd.Series(0.0, index=tranche_months.index)
    for name in TRANCHE_COLUMNS:
        rate_sum = rate_sum + tranche_months[name] / 12 * _RATE_BY_TRANCHE[name]
    return rate_sum


def predict_tier1(평균기준소득월액: pd.Series, tranche_months: pd.DataFrame) -> pd.Series:
    """Tier 1 잠정 비교모형: 예측 연금월액 = 평균기준소득월액 x sum(연도별 요율 x 월수/12)."""
    return 평균기준소득월액 * legal_rate_sum(tranche_months)
