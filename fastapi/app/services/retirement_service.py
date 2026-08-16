import math

from app.schemas.retirement import (
    Gender,
    ReadinessStatus,
    RecommendationResult,
    RecommendationType,
    ReductionResult,
    ScenarioOutcome,
    ScenariosResult,
    ScenarioType,
    SimulationResult,
    TimelinePoint,
)
from app.services.employees_service import LUMP_SUM_CONVERSION_FACTOR, PENSION_RATE
from app.services.reduction_rules import calculate_bracket_reduction, get_reduction_rule
from app.services.service_cap_rules import resolve_pension_service_cap_months

INVESTMENT_RETURN = 0.03  # 자산 운용 수익률
INFLATION_RATE = 0.02  # 물가상승률 (지출/Gap 증가율)
PENSION_GROWTH_RATE = 0.0  # 연금 소득 증가율
MAX_AGE = 100  # 시뮬레이션 상한 나이
TARGET_AGE_MALE = 84  # 남성 목표연령 (통계청 생명표 60세 기대여명 기준)
TARGET_AGE_FEMALE = 88  # 여성 목표연령 (통계청 생명표 60세 기대여명 기준)
SAVING_CAP_RATIO = 0.3  # 절약 상한 비율 (월 생활비 대비)
SEARCH_PRECISION = 0.01  # 이진탐색 종료 정밀도 (만원)
MAX_REDUCTION_RATIO = 0.5  # 감액 상한 비율 (노령연금액의 1/2 초과 감액 불가)
EARLY_REDUCTION_RATE_PER_YEAR = 0.05  # 조기수령 미달연수 1년당 감액률 (사학연금 조기퇴직연금 기준, 평생 적용)
EARLY_YEARS_MAX = 5  # 조기수령 최대 미달연수 (5년 초과는 조기수령 대상이 아님 -> 유효성 에러)
LUMP_SUM_SQUARE_FACTOR = 65 / 10000  # 공제일시금 2차 계수 (공제연수 제곱 가산분, 사학연금공단 공제일시금 산식)
MIN_PENSION_YEARS = 10  # 연금 선택 최소 연수 (공제일시금 일부 선택 시)
MAX_DEDUCTION_YEARS = 26  # 공제일시금 선택 최대 연수


def get_target_age(gender: Gender) -> int:
    """성별에 따른 목표연령 반환"""
    if gender == Gender.MALE:
        return TARGET_AGE_MALE
    return TARGET_AGE_FEMALE


def calculate_status(depletion_age: int | None, target_age: int) -> ReadinessStatus:
    """자산 고갈 나이와 목표연령을 비교해 노후 준비 상태 판정"""
    if depletion_age is None:
        return ReadinessStatus.SUFFICIENT
    if depletion_age >= target_age:
        return ReadinessStatus.MIDDLE
    return ReadinessStatus.INSUFFICIENT


def simulate_retirement(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: Gender,
) -> SimulationResult:
    """현재 나이부터 MAX_AGE까지 매년 자산 변화를 시뮬레이션하는 공용 계산 코어.
    diagnosis/recommendations API는 모두 이 함수(별칭 diagnose_core)를 통해서만 시뮬레이션을 수행한다.
    """
    if monthly_expenses <= 0:
        raise ValueError("monthly_expenses는 0보다 커야 합니다.")

    monthly_gap = monthly_expenses - monthly_pension

    annual_income = monthly_pension * 12
    annual_expense = monthly_expenses * 12
    annual_gap = annual_expense - annual_income

    current_asset = asset
    cumulative_gap = 0.0
    depletion_age: int | None = None
    timeline: list[TimelinePoint] = []

    for age in range(current_age, MAX_AGE + 1):
        cumulative_gap += annual_gap
        timeline.append(
            TimelinePoint(
                age=age,
                asset=current_asset,
                annual_income=annual_income,
                annual_expense=annual_expense,
                annual_gap=annual_gap,
                cumulative_annual_gap=cumulative_gap,
            )
        )

        current_asset = (current_asset - annual_gap) * (1 + INVESTMENT_RETURN)

        if depletion_age is None and annual_gap > 0 and current_asset <= 0:
            depletion_age = age + 1

        if current_asset < 0:
            current_asset = 0.0

        annual_expense *= 1 + INFLATION_RATE
        annual_income *= 1 + PENSION_GROWTH_RATE
        annual_gap = annual_expense - annual_income

    if depletion_age is not None:
        depletion_age = min(depletion_age, MAX_AGE)

    target_age = get_target_age(gender)
    status = calculate_status(depletion_age, target_age)

    return SimulationResult(
        current_age=current_age,
        monthly_gap=monthly_gap,
        depletion_age=depletion_age,
        depleted=depletion_age is not None,
        target_age=target_age,
        status=status,
        timeline=timeline,
    )


diagnose_core = simulate_retirement  # diagnosis/recommendations 공용 코어에 대한 별칭


def _binary_search_min(
    condition,
    low: float,
    high: float,
    precision: float = SEARCH_PRECISION,
) -> float:
    """[low, high] 구간에서 condition(x)가 True인 최소 x를 이진탐색으로 반환.
    condition은 x에 대해 단조(False->True)이며 condition(high)는 True여야 한다.
    """
    while high - low > precision:
        mid = (low + high) / 2
        if condition(mid):
            high = mid
        else:
            low = mid
    return high


def _expand_upper_bound(condition, seed: float, max_doublings: int = 60) -> float:
    """condition이 True가 될 때까지 상한을 2배씩 늘려가며 이진탐색용 구간을 확보"""
    high = max(seed, 1.0)
    for _ in range(max_doublings):
        if condition(high):
            return high
        high *= 2
    raise ValueError("추가 소득 필요액을 찾을 수 없습니다.")


def _round_up(value: float, decimals: int = 2) -> float:
    """이진탐색으로 찾은 최소값을 내림 없이 올림하여, 반올림으로 인해
    목표연령 도달 조건을 다시 벗어나지 않도록 보장한다."""
    factor = 10**decimals
    return math.ceil(value * factor) / factor


def recommend_retirement(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: Gender,
) -> RecommendationResult:
    """MIDDLE/INSUFFICIENT 진단 시 목표연령 도달에 필요한 최소 절약액/추가소득액을 계산.

    판정 캐스케이드:
      1) 생활비를 SAVING_CAP_RATIO 한도 내에서 절약하는 것만으로 목표연령에 도달하는지 확인
      2) 절약 상한까지 적용해도 부족하면, 절약 상한을 고정한 채 추가로 필요한 최소 월 소득을 탐색
    모든 시뮬레이션은 diagnose_core()에 위임하며 별도의 자산 계산 로직을 두지 않는다.
    """
    baseline = diagnose_core(
        current_age=current_age,
        monthly_expenses=monthly_expenses,
        monthly_pension=monthly_pension,
        asset=asset,
        gender=gender,
    )

    if baseline.status == ReadinessStatus.SUFFICIENT:
        return RecommendationResult(
            current_age=current_age,
            recommendation_type=RecommendationType.SUFFICIENT,
            required_saving=0.0,
            required_income=0.0,
            target_status=ReadinessStatus.SUFFICIENT,
            depletion_age=baseline.depletion_age,
            depleted=baseline.depleted,
            target_age=baseline.target_age,
            status=baseline.status,
            timeline=baseline.timeline,
        )

    def reaches_target(saving: float, extra_income: float) -> bool:
        result = diagnose_core(
            current_age=current_age,
            monthly_expenses=monthly_expenses - saving,
            monthly_pension=monthly_pension + extra_income,
            asset=asset,
            gender=gender,
        )
        return result.status == ReadinessStatus.SUFFICIENT

    saving_cap = monthly_expenses * SAVING_CAP_RATIO

    if reaches_target(saving_cap, 0.0):
        required_saving = _round_up(_binary_search_min(lambda s: reaches_target(s, 0.0), 0.0, saving_cap))
        required_income = 0.0
        recommendation_type = RecommendationType.SAVING_ONLY
    else:
        required_saving = _round_up(saving_cap)
        upper = _expand_upper_bound(lambda y: reaches_target(saving_cap, y), monthly_expenses)
        required_income = _round_up(_binary_search_min(lambda y: reaches_target(saving_cap, y), 0.0, upper))
        recommendation_type = RecommendationType.SAVING_AND_INCOME

    # 보고되는 required_saving/required_income(올림 처리된 값)로 다시 시뮬레이션하여
    # 응답의 timeline/status가 실제 추천값과 항상 일치하도록 보장한다.
    improved = diagnose_core(
        current_age=current_age,
        monthly_expenses=monthly_expenses - required_saving,
        monthly_pension=monthly_pension + required_income,
        asset=asset,
        gender=gender,
    )

    return RecommendationResult(
        current_age=current_age,
        recommendation_type=recommendation_type,
        required_saving=required_saving,
        required_income=required_income,
        target_status=ReadinessStatus.SUFFICIENT,
        depletion_age=improved.depletion_age,
        depleted=improved.depleted,
        target_age=improved.target_age,
        status=improved.status,
        timeline=improved.timeline,
    )


def simulate_pension_reduction(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: Gender,
    reemployment_income: float,
    year: int | None = None,
) -> ReductionResult:
    """재취업 예상 월소득에 따른 국민연금 소득심사 감액을 계산하고,
    감액된 연금으로 diagnose_core()를 통해 timeline을 재계산한다.
    자산 시뮬레이션 로직은 diagnose_core()에 전적으로 위임하며, 여기서는
    감액 산식(reduction_rules)만 계산한다.
    """
    if reemployment_income < 0:
        raise ValueError("reemployment_income은 0 이상이어야 합니다.")

    rule = get_reduction_rule(year)
    excess_income = max(0.0, reemployment_income - rule.threshold)
    raw_reduction = calculate_bracket_reduction(excess_income, rule.rate_brackets)
    monthly_reduction = min(raw_reduction, monthly_pension * MAX_REDUCTION_RATIO)
    reduced_monthly_pension = monthly_pension - monthly_reduction

    result = diagnose_core(
        current_age=current_age,
        monthly_expenses=monthly_expenses,
        monthly_pension=reduced_monthly_pension,
        asset=asset,
        gender=gender,
    )

    return ReductionResult(
        current_age=current_age,
        reemployment_income=reemployment_income,
        monthly_reduction=round(monthly_reduction, 2),
        reduced_monthly_pension=round(reduced_monthly_pension, 2),
        full_payment_income_threshold=rule.threshold,
        depletion_age=result.depletion_age,
        depleted=result.depleted,
        target_age=result.target_age,
        status=result.status,
        timeline=result.timeline,
    )


def _calculate_lump_sum_and_pension(
    base_monthly_income: float,
    total_service_years: float,
    deduction_years: float,
) -> tuple[float, float]:
    """공제일시금(퇴직연금공제일시금 방식)과 잔여 연금을 계산한다.

    공제일시금 = 기준소득월액 x 공제연수 x (LUMP_SUM_CONVERSION_FACTOR + LUMP_SUM_SQUARE_FACTOR x 공제연수)
    (사학연금공단 공식: 기준소득월액x(공제재직월수/12)x975/1000 + 기준소득월액x(공제재직월수/12)^2x65/10000)

    연금 부분은 재직연수를 '연금 선택 연수'(=min(총재직연수, 재직기간 상한)-공제연수)로
    치환해 employees_service의 기존 퇴직연금 산식(PENSION_RATE)을 그대로 재사용한다.
    상한을 먼저 적용한 뒤 공제연수를 빼야 한다 — 순서를 바꾸면(공제연수를 먼저 뺀 뒤
    상한을 적용하면) 총재직연수가 상한을 넘는 사람의 공제 효과가 왜곡된다.

    ScenariosRequest에는 2016.1.1 시점 재직기간 입력이 없으므로 여기서는 항상
    resolve_pension_service_cap_months(None) -> 본칙 36년(cap_basis=DEFAULT_MAX)을
    적용한다. 이전에는 이 상한 자체가 없어 total_service_years(최대 100년, 스키마
    제약)가 그대로 연금 선택 연수 계산에 들어갔다 — 확정 결함이었다(engine_defects.md).

    deduction_years == total_service_years(전액 공제)이면 연금 선택 연수가 0이 되어
    monthly_pension=0, lump_sum은 곧 퇴직연금일시금(LUMP_SUM) 산식과 동일해진다 —
    LUMP_SUM/SPLIT(분할) 두 시나리오 모두 이 함수 하나로 계산한다(중복 계산 없음).
    """
    lump_sum = base_monthly_income * deduction_years * (
        LUMP_SUM_CONVERSION_FACTOR + LUMP_SUM_SQUARE_FACTOR * deduction_years
    )
    cap_months, _cap_basis = resolve_pension_service_cap_months(None)
    capped_service_years = min(total_service_years, cap_months / 12)
    pension_years = capped_service_years - deduction_years
    monthly_pension = base_monthly_income * pension_years * PENSION_RATE
    return lump_sum, monthly_pension


def _resolve_split_deduction_years(total_service_years: int, deduction_years: int | None) -> int:
    """SPLIT(분할수령) 시나리오의 공제연수를 결정하고 제약을 검증한다.

    제약: 연금 선택 기간(=총재직연수-공제연수) >= MIN_PENSION_YEARS, 공제연수 <= MAX_DEDUCTION_YEARS.
    deduction_years가 주어지지 않으면 제약을 만족하는 최댓값으로 클램프한다.
    """
    max_allowed = min(total_service_years - MIN_PENSION_YEARS, MAX_DEDUCTION_YEARS)

    if deduction_years is None:
        if max_allowed < 0:
            raise ValueError(
                f"총 재직연수가 {MIN_PENSION_YEARS}년 미만이면 분할수령(SPLIT)을 선택할 수 없습니다."
            )
        return max_allowed

    if deduction_years < 0 or deduction_years > MAX_DEDUCTION_YEARS:
        raise ValueError(f"deduction_years는 0~{MAX_DEDUCTION_YEARS} 사이여야 합니다.")
    if total_service_years - deduction_years < MIN_PENSION_YEARS:
        raise ValueError(f"연금 선택 기간(총재직연수-deduction_years)은 {MIN_PENSION_YEARS}년 이상이어야 합니다.")

    return deduction_years


def _cumulative_received(timeline: list[TimelinePoint], upfront: float) -> list[float]:
    """timeline과 같은 순서(나이 오름차순)로, 각 시점까지의 누적 수령액(업프론트 일시금 포함)을 반환"""
    cumulative: list[float] = []
    running = upfront
    for point in timeline:
        running += point.annual_income
        cumulative.append(running)
    return cumulative


def _calculate_break_even_age(
    timeline: list[TimelinePoint],
    normal_cumulative: list[float],
    scenario_cumulative: list[float],
) -> int | None:
    """NORMAL 대비 손익분기 나이: NORMAL의 누적 수령액이 이 시나리오의 누적 수령액을
    처음으로 따라잡거나 넘어서는 나이. 끝까지 따라잡지 못하면(이 시나리오가 항상 유리) None."""
    for point, normal_cum, scenario_cum in zip(timeline, normal_cumulative, scenario_cumulative):
        if normal_cum >= scenario_cum:
            return point.age
    return None


def _early_reduction_rate(early_years: float) -> float:
    """조기수령 미달연수(early_years, 소수 허용)에 대한 감액률.

    사학연금 조기퇴직연금 감액표(연 단위 계단식): 1년 이내 5%, 1년 초과~2년 이내
    10%, 2년 초과~3년 이내 15%, 3년 초과~4년 이내 20%, 4년 초과~5년 이내 25%.
    즉 감액률 = EARLY_REDUCTION_RATE_PER_YEAR x ceil(early_years) — 정수를 넣으면
    이전 버전의 선형식(EARLY_REDUCTION_RATE_PER_YEAR x early_years)과 결과가
    같다(정수는 자기 자신의 올림과 같으므로).
    """
    return EARLY_REDUCTION_RATE_PER_YEAR * math.ceil(early_years)


def simulate_scenarios(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: Gender,
    base_monthly_income: float,
    total_service_years: int,
    early_years: float = EARLY_YEARS_MAX,
    deduction_years: int | None = None,
) -> ScenariosResult:
    """정상/조기/일시금/분할 4가지 연금 수령방식을 diagnose_core()에 파라미터만 바꿔
    순차(동기 for 루프)로 실행하고 비교한다. 자산 시뮬레이션 로직은 diagnose_core()에
    전적으로 위임하며, 방식별 monthly_pension/asset 조합만 여기서 계산한다.

    NORMAL/EARLY는 입력된 monthly_pension을 그대로 사용하고, LUMP_SUM/SPLIT는
    기준소득월액(base_monthly_income)·총재직연수(total_service_years) 기반
    공제일시금 산식(_calculate_lump_sum_and_pension)으로 재계산한다.
    총 수령액은 모든 시나리오에 대해 동일하게 current_age~MAX_AGE 기간으로 합산한다.

    early_years(미달연수)는 소수를 허용한다 — 감액률은 연 단위 계단식(올림)으로
    _early_reduction_rate()가 계산하며, 정수를 넣으면 이전 버전(선형식)과 동일한
    결과를 낸다(회귀 테스트로 고정, tests/test_retirement_service.py 참조).

    TODO(스코프 밖): 미달연수를 "법정 지급개시연령 - 실제 수령개시연령"으로
    서버가 직접 산정하는 기능은 이번 트랙에 포함하지 않았다. 지급개시연령은
    사학연금법령 개정사항(2016.1.1, 4항)에 따라 퇴직연도별로 60~65세까지
    단계적으로 연장되는 별도 표가 필요하다 — 확보 후 별도 이슈로 진행
    (backtest/reports/scope_limitations.md 향후 과제 참조). 현재는 호출자가
    early_years를 직접 산정해 넘겨야 한다.
    """
    if not (0 < early_years <= EARLY_YEARS_MAX):
        raise ValueError(f"early_years는 0보다 크고 {EARLY_YEARS_MAX} 이하여야 합니다.")
    if total_service_years <= 0:
        raise ValueError("total_service_years는 0보다 커야 합니다.")

    # LUMP_SUM: 전액 공제(공제연수=총재직연수) -> 연금 선택 연수 0, 공제일시금 산식만 남음
    full_lump_sum, full_pension = _calculate_lump_sum_and_pension(
        base_monthly_income, total_service_years, total_service_years
    )

    # SPLIT(분할수령): 요청된(또는 제약 내 최댓값으로 클램프된) 공제연수만큼만 일시금으로 전환
    split_deduction_years = _resolve_split_deduction_years(total_service_years, deduction_years)
    split_lump_sum, split_pension = _calculate_lump_sum_and_pension(
        base_monthly_income, total_service_years, split_deduction_years
    )

    scenario_inputs: dict[ScenarioType, tuple[float, float]] = {
        ScenarioType.NORMAL: (monthly_pension, asset),
        ScenarioType.EARLY: (monthly_pension * (1 - _early_reduction_rate(early_years)), asset),
        ScenarioType.LUMP_SUM: (full_pension, asset + full_lump_sum),
        ScenarioType.INSTALLMENT: (split_pension, asset + split_lump_sum),
    }

    simulated: dict[ScenarioType, tuple[SimulationResult, float, list[float]]] = {}
    for scenario_type, (scenario_pension, scenario_asset) in scenario_inputs.items():
        result = diagnose_core(
            current_age=current_age,
            monthly_expenses=monthly_expenses,
            monthly_pension=scenario_pension,
            asset=scenario_asset,
            gender=gender,
        )
        upfront = scenario_asset - asset  # 초기 자산에 더해진 일시금(있는 경우)
        cumulative = _cumulative_received(result.timeline, upfront)
        simulated[scenario_type] = (result, upfront, cumulative)

    normal_result, _normal_upfront, normal_cumulative = simulated[ScenarioType.NORMAL]

    outcomes: list[ScenarioOutcome] = []
    for scenario_type, (result, _upfront, cumulative) in simulated.items():
        total_received = cumulative[-1] if cumulative else 0.0
        break_even_age = (
            None
            if scenario_type == ScenarioType.NORMAL
            else _calculate_break_even_age(normal_result.timeline, normal_cumulative, cumulative)
        )

        outcomes.append(
            ScenarioOutcome(
                scenario_type=scenario_type,
                depletion_age=result.depletion_age,
                depleted=result.depleted,
                total_received=round(total_received, 2),
                break_even_age=break_even_age,
                timeline=result.timeline,
            )
        )

    return ScenariosResult(
        current_age=current_age,
        scenarios=outcomes,
        best_scenario=_select_best_scenario(outcomes),
    )


def _select_best_scenario(outcomes: list[ScenarioOutcome]) -> ScenarioType:
    """고갈 나이가 가장 큰 시나리오를 선택하고, 동률이면 총 수령액이 큰 시나리오를 선택한다.
    depletion_age가 None(무고갈)인 시나리오는 가장 늦게 고갈되는 것으로 간주해 최우선한다."""

    def sort_key(outcome: ScenarioOutcome) -> tuple[float, float]:
        depletion_for_sort = outcome.depletion_age if outcome.depletion_age is not None else math.inf
        return (depletion_for_sort, outcome.total_received)

    best = max(outcomes, key=sort_key)
    return best.scenario_type
