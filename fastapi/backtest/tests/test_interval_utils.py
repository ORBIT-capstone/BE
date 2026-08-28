import numpy as np
import pandas as pd
from interval_utils import (
    ALLOWANCE_BOUNDS_MANWON,
    LUMPSUM_BOUNDS_MANWON,
    PENSION_BOUNDS_MANWON,
    bounds_to_won_maps,
    is_hit,
)


def test_pension_bounds_code0_is_nan():
    lower, upper = bounds_to_won_maps(PENSION_BOUNDS_MANWON)
    assert np.isnan(lower[0])
    assert np.isnan(upper[0])


def test_pension_bounds_won_conversion():
    lower, upper = bounds_to_won_maps(PENSION_BOUNDS_MANWON)
    # 코드 1: 0~50만원 -> 0~500,000원
    assert lower[1] == 0
    assert upper[1] == 500_000
    # 코드 2: 50~100만원 -> 500,000~1,000,000원
    assert lower[2] == 500_000
    assert upper[2] == 1_000_000


def test_pension_bounds_top_code_open_upper():
    lower, upper = bounds_to_won_maps(PENSION_BOUNDS_MANWON)
    assert lower[8] == 3_500_000
    assert upper[8] == np.inf


def test_allowance_bounds_top_code():
    lower, upper = bounds_to_won_maps(ALLOWANCE_BOUNDS_MANWON)
    assert lower[9] == 35_000_000
    assert upper[9] == np.inf


def test_lumpsum_bounds_top_code():
    lower, upper = bounds_to_won_maps(LUMPSUM_BOUNDS_MANWON)
    assert lower[17] == 130_000_000
    assert upper[17] == np.inf


def test_lumpsum_bounds_all_codes_present():
    lower, upper = bounds_to_won_maps(LUMPSUM_BOUNDS_MANWON)
    assert set(lower.keys()) == set(range(18))
    assert set(upper.keys()) == set(range(18))


def test_is_hit_within_range():
    predicted = pd.Series([100.0, 499_999.0, 500_000.0, 999_999.0, 1_000_000.0])
    lower = pd.Series([500_000.0] * 5)
    upper = pd.Series([1_000_000.0] * 5)
    result = is_hit(predicted, lower, upper)
    assert list(result) == [False, False, True, True, False]


def test_is_hit_open_upper_bound():
    predicted = pd.Series([10_000_000.0, 1e18])
    lower = pd.Series([3_500_000.0, 3_500_000.0])
    upper = pd.Series([np.inf, np.inf])
    result = is_hit(predicted, lower, upper)
    assert list(result) == [True, True]
