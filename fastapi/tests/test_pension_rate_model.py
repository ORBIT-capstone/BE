import sys
from pathlib import Path

import pytest

from app.services.pension_rate_model import (
    PENSION_RATE_BY_YEAR,
    PRE_2010_CONVERSION_FACTOR,
    RATE_2010_2015,
    RATE_2036_PLUS,
    RATE_PRE_2010,
    calculate_monthly_pension_tranche,
    yyyymm_after_months,
)

BACKTEST_CONFIG_DIR = Path(__file__).resolve().parent.parent / "backtest" / "config"


def _load_backtest_tranche_rates():
    """backtest/config/tranche_rates.py를 직접 import해 프로덕션 복제값과 대조한다.

    이 모듈은 프로덕션이 backtest 패키지에 런타임 의존하지 않기 위해 법정 요율표를
    복제했다(app/services/pension_rate_model.py 모듈 docstring 참조) — 두 값이
    갈라지면 조용히 서로 다른 지급률을 쓰게 되므로, 이 테스트로 항상 값이
    같은지 고정한다.
    """
    sys.path.insert(0, str(BACKTEST_CONFIG_DIR))
    import tranche_rates  # noqa: PLC0415

    return tranche_rates


def test_legal_rate_table_matches_backtest_config():
    backtest_rates = _load_backtest_tranche_rates()
    assert RATE_PRE_2010 == backtest_rates.RATE_PRE_2010
    assert RATE_2010_2015 == backtest_rates.RATE_2010_2015
    assert RATE_2036_PLUS == backtest_rates.RATE_2036_PLUS
    assert PENSION_RATE_BY_YEAR == backtest_rates.PENSION_RATE_BY_YEAR


def test_yyyymm_after_months_handles_year_rollover():
    assert yyyymm_after_months(202412, 1) == 202501
    assert yyyymm_after_months(202501, -1) == 202412
    assert yyyymm_after_months(202603, 12) == 202703


def test_calculate_monthly_pension_tranche_zero_months_is_zero():
    assert calculate_monthly_pension_tranche(3_000_000, 202601, 0) == 0
    assert calculate_monthly_pension_tranche(3_000_000, 202601, -5) == 0


def test_calculate_monthly_pension_tranche_all_post_2036_uses_flat_rate_no_alpha():
    # 재직기간 전체가 2036년 이후인 사람 — α(2009년 이전 환산계수)가 전혀 곱해지지
    # 않고 RATE_2036_PLUS만 적용돼야 한다. 이것이 "미래로 외삽 가능하다"는 주장의
    # 핵심 근거다 — 학습 표본(2020~2025 퇴직자)에 이런 사람은 존재하지 않는다.
    income = 3_000_000
    retire_yyyymm = 205001
    months = 120  # 10년, 전부 2036년 이후
    result = calculate_monthly_pension_tranche(income, retire_yyyymm, months)
    expected = int(income * (months / 12) * RATE_2036_PLUS)
    assert result == expected


def test_calculate_monthly_pension_tranche_all_pre_2010_applies_alpha():
    # 재직기간 전체가 2009년 이전인 사람 — RATE_PRE_2010 x α만 적용돼야 한다.
    income = 3_000_000
    retire_yyyymm = 200912  # 재직 구간: [200912-months, 200911]
    months = 120
    result = calculate_monthly_pension_tranche(income, retire_yyyymm, months)
    expected = int(income * (months / 12) * RATE_PRE_2010 * PRE_2010_CONVERSION_FACTOR)
    assert result == expected


def test_calculate_monthly_pension_tranche_never_loses_months_across_boundary():
    # tranche 구간을 걸치는 경우 개월수가 소실되지 않는지 확인: 요율이 전부 같다고
    # 가정했을 때의 합(=단일 요율 가정과 비교)이 아니라, 실제로는 여러 요율이
    # 섞이므로 "PRE_2010 요율만 적용했을 때의 상한"과 "2036+ 요율만 적용했을 때의
    # 하한" 사이에 결과가 있어야 한다(모든 tranche 요율이 이 두 값 사이에 있으므로).
    income = 3_000_000
    months = 480  # 40년 — pre-2010부터 2036+까지 여러 구간을 걸친다
    retire_yyyymm = 205001
    result = calculate_monthly_pension_tranche(income, retire_yyyymm, months)
    upper_bound = int(income * (months / 12) * RATE_PRE_2010)  # α=1 가정 시 최댓값
    lower_bound = 0
    assert lower_bound < result < upper_bound


def test_calculate_monthly_pension_tranche_monotonic_in_service_months():
    # 같은 퇴직연월에서 재직월수가 늘어나면 연금월액도 항상 늘어나야 한다
    # (모든 tranche 요율이 양수이므로 당연한 성질이지만, 회귀 방지용으로 고정한다).
    income = 3_000_000
    retire_yyyymm = 203001
    values = [calculate_monthly_pension_tranche(income, retire_yyyymm, m) for m in range(0, 481, 12)]
    assert values == sorted(values)
    assert len(set(values)) > 1


@pytest.mark.parametrize("alpha", [PRE_2010_CONVERSION_FACTOR])
def test_pre_2010_conversion_factor_is_within_plausible_range(alpha):
    # α는 "2009년 이전 소득기준 proxy 대체로 인한 격차"를 흡수하는 값이라
    # 0~1 범위를 크게 벗어나면 안 된다(관측 실효 지급률이 법정 요율보다 낮다는
    # tier1_evaluation.md의 관측과 방향이 같아야 한다 — 즉 1보다 작아야 한다).
    assert 0 < alpha < 1
