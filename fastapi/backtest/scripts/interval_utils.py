"""구간 코드 <-> 원 단위 하한/상한 변환, 적중 판정 공용 유틸.

제공기관 공지 구간 정의 (단위: 만원, [이상, 미만)). None은 개방 경계.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MANWON_TO_WON = 10_000

PENSION_BOUNDS_MANWON: dict[int, tuple[float | None, float | None]] = {
    0: (None, None),
    1: (0, 50),
    2: (50, 100),
    3: (100, 150),
    4: (150, 200),
    5: (200, 250),
    6: (250, 300),
    7: (300, 350),
    8: (350, None),
}

ALLOWANCE_BOUNDS_MANWON: dict[int, tuple[float | None, float | None]] = {
    0: (None, None),
    1: (0, 100),
    2: (100, 500),
    3: (500, 1000),
    4: (1000, 1500),
    5: (1500, 2000),
    6: (2000, 2500),
    7: (2500, 3000),
    8: (3000, 3500),
    9: (3500, None),
}

LUMPSUM_BOUNDS_MANWON: dict[int, tuple[float | None, float | None]] = {
    0: (None, None),
    1: (0, 100),
    2: (100, 200),
    3: (200, 300),
    4: (300, 400),
    5: (400, 500),
    6: (500, 600),
    7: (600, 700),
    8: (700, 800),
    9: (800, 900),
    10: (900, 1000),
    11: (1000, 3000),
    12: (3000, 5000),
    13: (5000, 7000),
    14: (7000, 9000),
    15: (9000, 11000),
    16: (11000, 13000),
    17: (13000, None),
}


def bounds_to_won_maps(
    bounds_manwon: dict[int, tuple[float | None, float | None]],
) -> tuple[dict[int, float], dict[int, float]]:
    """만원 단위 구간 정의를 (하한_map, 상한_map) 원 단위 dict로 변환한다.

    코드 0은 상/하한 모두 NaN("해당 금액 없음"), 최상단 개방구간의 상한은 np.inf.
    """
    lower_map: dict[int, float] = {}
    upper_map: dict[int, float] = {}
    for code, (lo, hi) in bounds_manwon.items():
        lower_map[code] = np.nan if lo is None else lo * MANWON_TO_WON
        upper_map[code] = np.nan if (lo is None and hi is None) else (
            np.inf if hi is None else hi * MANWON_TO_WON
        )
    return lower_map, upper_map


def is_hit(predicted: pd.Series, lower: pd.Series, upper: pd.Series) -> pd.Series:
    """구간 적중 판정: lower <= predicted < upper."""
    return (predicted >= lower) & (predicted < upper)
