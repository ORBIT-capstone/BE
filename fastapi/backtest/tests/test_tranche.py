import pandas as pd
from tranche import decompose_tranche_months, idx_from_yyyymm, predict_tier1


def test_idx_from_yyyymm_monotonic():
    s = pd.Series([202001, 202002, 202101])
    idx = idx_from_yyyymm(s)
    assert idx.iloc[1] - idx.iloc[0] == 1
    assert idx.iloc[2] - idx.iloc[1] == 11


def test_decompose_sum_matches_months_within_single_tranche():
    # 2020-01 임용, 24개월 재직 -> 전부 2020~2021년(요율 tranche) 안에 있음
    appointed = pd.Series([202001])
    months = pd.Series([24])
    tm = decompose_tranche_months(appointed, months)
    assert tm.sum(axis=1).iloc[0] == 24
    assert tm["y2020"].iloc[0] == 12
    assert tm["y2021"].iloc[0] == 12


def test_decompose_sum_matches_months_spanning_pre_2010_and_2010_2015():
    # 2008-06 임용, 84개월(7년) 재직 -> 2008-06~2015-05
    appointed = pd.Series([200806])
    months = pd.Series([84])
    tm = decompose_tranche_months(appointed, months)
    assert tm.sum(axis=1).iloc[0] == 84
    # 2008-06~2009-12: 19개월
    assert tm["pre_2010"].iloc[0] == 19
    # 2010-01~2015-05: 65개월
    assert tm["y2010_2015"].iloc[0] == 65


def test_decompose_sum_assertion_holds_across_many_rows():
    appointed = pd.Series([199501, 200003, 201206, 201801])
    months = pd.Series([300, 180, 60, 36])
    tm = decompose_tranche_months(appointed, months)
    assert (tm.sum(axis=1) == months).all()


def test_decompose_never_loses_months_far_future():
    # 회귀 테스트: 예전 버전은 tranche 구간이 2025년에서 끝나(현재는 2035년) 그 이후로
    # 뻗는 재직기간의 월수를 조용히 버렸다. 2036+ 무한 꼬리 구간 추가로 고정.
    appointed = pd.Series([203603])
    months = pd.Series([24])  # 2036-03 ~ 2038-02, 전부 y2036_plus 꼬리 구간
    tm = decompose_tranche_months(appointed, months)
    assert tm.sum(axis=1).iloc[0] == 24
    assert tm["y2036_plus"].iloc[0] == 24

    appointed2 = pd.Series([203503])
    months2 = pd.Series([24])  # 2035-03~2036-02, 2035년 10개월 + 2036+ 꼬리 14개월로 분해
    tm2 = decompose_tranche_months(appointed2, months2)
    assert tm2.sum(axis=1).iloc[0] == 24
    assert tm2["y2035"].iloc[0] == 10
    assert tm2["y2036_plus"].iloc[0] == 14


def test_decompose_never_loses_months_far_past():
    appointed = pd.Series([194001])
    months = pd.Series([500])
    tm = decompose_tranche_months(appointed, months)
    assert tm.sum(axis=1).iloc[0] == 500


def test_decompose_never_loses_months_extreme_offset():
    appointed = pd.Series([202001])
    months = pd.Series([300])
    for offset in [-1200, -24, -12, 0, 12, 24, 1200]:
        tm = decompose_tranche_months(appointed, months, offset_months=offset)
        assert tm.sum(axis=1).iloc[0] == 300, f"offset={offset}에서 월수 소실"


def test_decompose_offset_shifts_window_but_preserves_length():
    appointed = pd.Series([201501])
    months = pd.Series([36])
    tm_0 = decompose_tranche_months(appointed, months, offset_months=0)
    tm_shifted = decompose_tranche_months(appointed, months, offset_months=-12)
    assert tm_0.sum(axis=1).iloc[0] == 36
    assert tm_shifted.sum(axis=1).iloc[0] == 36
    # 1년 앞당기면 2015년 비중이 늘고 2017년 비중이 준다
    assert tm_shifted["y2010_2015"].iloc[0] > tm_0["y2010_2015"].iloc[0]


def test_predict_tier1_zero_months_gives_zero():
    tm = pd.DataFrame({col: [0] for col in decompose_tranche_months(pd.Series([202001]), pd.Series([0])).columns})
    income = pd.Series([3_000_000.0])
    pred = predict_tier1(income, tm)
    assert pred.iloc[0] == 0
