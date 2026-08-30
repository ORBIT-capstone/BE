"""연금 지급률 모형 — 법정 연도별 지급률(tranche) + 2009년 이전 구간 환산계수(α).

## 배경

기존 엔진은 `PENSION_RATE=0.017` 단일 상수를 재직기간 전체에 적용했다. 그러나
사학연금법령 개정사항(2016.1.1)에 따르면 지급률은 연도별로 다르다
(2009년 이전 2.0%, 2010~2015년 1.9%, 2016년 이후 매년 인하되어 2035년 1.70%,
2036년 이후 1.70% 고정). 이 tranche 구조를 그대로 적용하는 것("법정 tranche"
모형, α=1)만으로는 백테스트 구간 적중률이 오히려 떨어진다 — 법정 요율이 전부
기존 0.017보다 높기 때문에, 요율만 올리면 이미 과대추정 위주였던 오차가 더
악화된다(`backtest/reports/calibration_report.md` 참조).

## α가 필요한 이유

2009년 이전 재직기간의 법정 산정기초는 평균보수월액인데, 우리가 가진 데이터와
API 입력값에는 이 값이 없다 — 평균기준소득월액(2010년 이후 개념)으로 대체할
수밖에 없다. 두 기준의 절대 수준이 달라 법정 요율(2.0%)을 그대로 곱하면
체계적으로 어긋난다. α는 이 대체로 생기는 격차를 흡수하는 **단일 스칼라**다.

**α는 법령상 근거가 있는 상수가 아니다.** "2009년 이전 구간의 평균보수월액을
평균기준소득월액으로 근사할 때 생기는 체계적 비율"을 사학연금공단 실적
데이터로 추정한 값이며, 그 이상의 의미를 부여하지 않는다.

## 이전 30-파라미터 모형과의 차이 (반드시 구분할 것)

`backtest/analysis/effective_rate_model_30param.py`(프로덕션 미채택, 철회됨)는
재직연수·소득·퇴직연도·퇴직연령·학교급×직구분 등 약 30개 계수를 전부 "적중률이
최대가 되도록" 데이터에 맞춘 것이었다 — `tier1_evaluation.md`가 명시적으로
경계한 "결과를 맞추기 위한 계수 조정"에 정확히 해당한다. 그 모형은 2020~2025년
퇴직자 실적의 재직기간 구성(2009년 이전 비중)을 통째로 학습했기 때문에, 그
구성이 다른 미래 퇴직자에게 체계적으로 틀릴 위험이 있었다.

이 모듈이 하는 일은 그것과 다르다: **조정하는 대상은 "결과"가 아니라 "데이터가
없는 항목(2009년 이전 소득 기준)의 대체값" 단 하나뿐**이고, 그 외의 모든 지급률은
법령이 확정한 값을 그대로 쓴다. 파라미터가 1개이므로 재직기간 구성이 다른
미래 퇴직자에게도 구조적으로 외삽 가능하다 — 재직기간이 전부 2009년 이후인
사람에게는 α가 아예 곱해지지 않고 법정 요율만 적용된다(아래 예시).

## 검증

5-fold 교차검증(α를 fold마다 재적합): 전체 구간 적중률 68.99%(±0.30%p),
닫힌구간 65.64%. 개선 전(단일 상수 0.017) 전체 43.54%/닫힌구간 19.99% 대비
개선됐으나, 프로덕션 미채택 30-파라미터 모형의 80.39%보다는 낮다 — 파라미터를
1개로 제한한 데 따른 정직한 트레이드오프다. 상세 비교는
`backtest/reports/calibration_report.md` 참조.

## α와 tier1_evaluation.md의 "관측실효/법정요율 비율(median 0.738)"의 관계

두 수치는 **정의가 다르다**. 0.738은 닫힌구간 전체 표본(2009년 이전·2010~2015년·
2016년 이후 재직기간이 섞인 사람들)의 관측 실효 지급률을 법정 요율 가중평균으로
나눈 비율의 중앙값이다. α=0.5311은 2009년 이전 구간에만 적용되는 배수다. 두
값 모두 1보다 작다는 **방향**은 같다 — 법정 요율을 그대로 쓰면 실제보다
과대추정한다는 관측과 일치한다. 하지만 **크기는 다르다**: 0.738은 여러 구간이
섞인 평균이고, α는 그중 격차가 가장 큰 것으로 추정되는 2009년 이전 구간만
분리해 추정한 값이라 더 작게 나온 것으로 해석한다(2009년 이전 재직기간
비중이 큰 장기재직자일수록 실효 지급률이 낮다는 관측, `baseline_report.md`
재직연수 구간별 표와도 방향이 일치한다).
"""

from __future__ import annotations

__all__ = ["calculate_monthly_pension_tranche", "yyyymm_after_months"]

# --- 사학연금법령 개정사항(2016.1.1) 연도별 지급률표 ---
# backtest/config/tranche_rates.py와 값이 동일해야 한다. 프로덕션이 backtest
# 패키지(분석 전용, pandas/numpy 의존)에 런타임 의존하지 않도록 값을 복제했다 —
# tests/test_pension_rate_model.py가 두 파일의 값 일치를 회귀 테스트로 고정한다.
RATE_PRE_2010 = 0.020  # ~2009-12-31
RATE_2010_2015 = 0.019  # 2010-01-01 ~ 2015-12-31

PENSION_RATE_BY_YEAR: dict[int, float] = {
    2016: 0.01878,
    2017: 0.01856,
    2018: 0.01834,
    2019: 0.01812,
    2020: 0.01790,
    2021: 0.01780,
    2022: 0.01770,
    2023: 0.01760,
    2024: 0.01750,
    2025: 0.01740,
    2026: 0.01736,
    2027: 0.01732,
    2028: 0.01728,
    2029: 0.01724,
    2030: 0.01720,
    2031: 0.01716,
    2032: 0.01712,
    2033: 0.01708,
    2034: 0.01704,
    2035: 0.01700,
}
RATE_2036_PLUS = 0.01700  # 2036년 이후 고정(법령상 인하 스케줄이 2035년 종료)

# 2009년 이전 구간 환산계수(α). backtest/scripts/fit_alpha 계열 스크립트로
# 5-fold 교차검증 적합(fold별 추정치 0.5311~0.5337, 표준편차 0.0012 — 매우
# 안정적이라 전체표본 적합값을 그대로 쓴다). 상세 근거는 모듈 docstring 참조.
PRE_2010_CONVERSION_FACTOR = 0.5311


def _idx(yyyymm: int) -> int:
    """YYYYMM 정수를 절대월 인덱스로 변환: idx = year*12 + (month-1)."""
    return (yyyymm // 100) * 12 + (yyyymm % 100 - 1)


_IDX_2010_01 = _idx(201001)
_IDX_2016_01 = _idx(201601)
_IDX_2036_01 = _idx(203601)


def yyyymm_after_months(base_yyyymm: int, months: int) -> int:
    """base_yyyymm으로부터 months개월 후의 YYYYMM (음수면 이전)."""
    idx = _idx(base_yyyymm) + months
    year, month = idx // 12, idx % 12 + 1
    return year * 100 + month


def _tranche_rate_sum(start_idx: int, end_idx: int) -> float:
    """[start_idx, end_idx](양끝 포함) 구간을 연도별 tranche로 나눠 rate*개월수/12 합을 구한다.

    구간이 비어 있으면(start_idx > end_idx) 0을 반환한다 — 재직월수가 0 이하인
    경우를 별도 분기 없이 처리하기 위함이다.
    """
    total = 0.0

    lo, hi = start_idx, min(end_idx, _IDX_2010_01 - 1)
    if hi >= lo:
        total += (hi - lo + 1) / 12 * RATE_PRE_2010 * PRE_2010_CONVERSION_FACTOR

    lo, hi = max(start_idx, _IDX_2010_01), min(end_idx, _IDX_2016_01 - 1)
    if hi >= lo:
        total += (hi - lo + 1) / 12 * RATE_2010_2015

    for year, rate in PENSION_RATE_BY_YEAR.items():
        y_lo, y_hi = _idx(year * 100 + 1), _idx(year * 100 + 12)
        lo, hi = max(start_idx, y_lo), min(end_idx, y_hi)
        if hi >= lo:
            total += (hi - lo + 1) / 12 * rate

    lo, hi = max(start_idx, _IDX_2036_01), end_idx
    if hi >= lo:
        total += (hi - lo + 1) / 12 * RATE_2036_PLUS

    return total


def calculate_monthly_pension_tranche(
    base_income: float, retire_yyyymm: int, capped_service_months: int
) -> int:
    """연금월액 = 기준소득월액 x sum(연도별 tranche 요율 x 해당 구간 개월수/12).

    재직 구간은 퇴직연월 직전 capped_service_months개월로 잡는다
    (`[retire_yyyymm의 전월 - capped_service_months + 1, retire_yyyymm의 전월]`) —
    재직기간이 법정 상한을 넘어 절단되는 경우, 절단되는 쪽은 경력 후반이 아니라
    **초반**이라고 가정한다. 이는 `backtest/scripts/build_clean_dataset.py`가
    실적 데이터에서 추정임용연월을 역산할 때 쓰는 것과 같은 가정이다(퇴직 시점
    기준으로 인정 재직월수만큼 거슬러 올라간다) — 두 곳의 가정을 다르게 두면
    산식과 백테스트 채점 기준이 서로 다른 재직기간 구성을 가정하게 되어 비교가
    무의미해진다.
    """
    if capped_service_months <= 0:
        return 0
    end_idx = _idx(retire_yyyymm) - 1  # 재직월수는 퇴직월 자체를 포함하지 않는다
    start_idx = end_idx - capped_service_months + 1
    rate_sum = _tranche_rate_sum(start_idx, end_idx)
    return int(base_income * rate_sum)
