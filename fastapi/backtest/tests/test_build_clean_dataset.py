import pandas as pd
from build_clean_dataset import (
    STATUTORY_CAP_MONTHS,
    _estimate_appointment_yyyymm,
    _is_service_months_capped,
    _yyyymmdd_to_yyyymm,
)


def test_yyyymmdd_to_yyyymm_drops_day():
    s = pd.Series([20200101, 20241231, 20200228])
    result = _yyyymmdd_to_yyyymm(s)
    assert list(result) == [202001, 202412, 202002]


def test_statutory_cap_months_values():
    assert STATUTORY_CAP_MONTHS == {396, 408, 420, 432}


def test_is_service_months_capped_exact_match_only():
    months = pd.Series([395, 396, 398, 408, 420, 432])
    result = _is_service_months_capped(months)
    assert list(result) == [False, True, False, True, True, True]


def test_is_service_months_capped_does_not_use_threshold():
    # 398, 420보다 큰 400 같은 임의값은 상한 집합의 원소가 아니므로 False여야 한다
    # (>= 396 방식이었다면 잘못 True가 됐을 값들)
    months = pd.Series([397, 400, 409, 500])
    result = _is_service_months_capped(months)
    assert list(result) == [False, False, False, False]


def test_estimate_appointment_yyyymm_off_by_one_convention():
    """재직월수는 퇴직월을 포함하지 않는다고 가정한다: 근무 구간은
    [추정임용연월, 퇴직연월 - 1개월]이며 길이가 재직월수와 같다.
    예: 퇴직 2020-01, 재직 16개월 -> 근무 구간 2018-09~2019-12(16개월) -> 임용 2018-09.
    """
    퇴직연월 = pd.Series([202001])
    재직월수 = pd.Series([16])
    result = _estimate_appointment_yyyymm(퇴직연월, 재직월수)
    assert result.iloc[0] == 201809


def test_estimate_appointment_yyyymm_year_boundary():
    # 퇴직 2021-03, 재직 24개월 -> 근무 구간 2019-03~2021-02 -> 임용 2019-03
    퇴직연월 = pd.Series([202103])
    재직월수 = pd.Series([24])
    result = _estimate_appointment_yyyymm(퇴직연월, 재직월수)
    assert result.iloc[0] == 201903


def test_estimate_appointment_yyyymm_roundtrip_length():
    """추정임용연월로부터 역산한 근무 개월수가 항상 원래 재직월수와 같아야 한다
    (build_clean_dataset의 off-by-one 관례를 고정하는 왕복 테스트)."""
    퇴직연월 = pd.Series([202001, 202412, 202506, 202001])
    재직월수 = pd.Series([16, 396, 120, 1])
    appointed = _estimate_appointment_yyyymm(퇴직연월, 재직월수)

    def idx(yyyymm: pd.Series) -> pd.Series:
        return (yyyymm // 100) * 12 + (yyyymm % 100 - 1)

    # 근무 구간은 [appointed, 퇴직연월 - 1개월] 이므로
    # idx(퇴직연월) - idx(appointed) == 재직월수 가 항상 성립해야 한다
    assert list(idx(퇴직연월) - idx(appointed)) == list(재직월수)
