import math

from app.schemas.retirement import (
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
from app.services.employees_service import LUMP_SUM_CONVERSION_FACTOR
from app.services.reduction_rules import calculate_bracket_reduction, get_reduction_rule

INVESTMENT_RETURN = 0.03  # 자산 운용 수익률
INFLATION_RATE = 0.02  # 물가상승률 (지출/Gap 증가율)
PENSION_GROWTH_RATE = 0.0  # 연금 소득 증가율
MAX_AGE = 100  # 시뮬레이션 상한 나이
TARGET_AGE_MALE = 84  # 남성 목표연령 (통계청 생명표 60세 기대여명 기준)
TARGET_AGE_FEMALE = 88  # 여성 목표연령 (통계청 생명표 60세 기대여명 기준)
SAVING_CAP_RATIO = 0.3  # 절약 상한 비율 (월 생활비 대비)
SEARCH_PRECISION = 0.01  # 이진탐색 종료 정밀도 (만원)
MAX_REDUCTION_RATIO = 0.5  # 감액 상한 비율 (노령연금액의 1/2 초과 감액 불가)
EARLY_REDUCTION_RATE = 0.3  # 조기수령 감액률 (5년 조기수령 시 월 0.5% x 60개월 최대 감액)
INSTALLMENT_SPLIT_RATIO = 0.5  # 분할수령 시 일시금/월연금 배분 비율


def get_target_age(gender: str) -> int:
    """성별에 따른 목표연령 반환"""
    if gender == "male":
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
    gender: str,
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
                income=annual_income,
                expense=annual_expense,
                gap=annual_gap,
                cumulative_gap=cumulative_gap,
            )
        )

        current_asset = (current_asset - annual_gap) * (1 + INVESTMENT_RETURN)

        if depletion_age is None and annual_gap > 0 and current_asset <= 0:
            depletion_age = age + 1

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
    gender: str,
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
            depletion_age=baseline.depletion_age,
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
        return result.status != ReadinessStatus.INSUFFICIENT

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
        depletion_age=improved.depletion_age,
        target_age=improved.target_age,
        status=improved.status,
        timeline=improved.timeline,
    )


def simulate_pension_reduction(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: str,
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
        target_age=result.target_age,
        status=result.status,
        timeline=result.timeline,
    )


def _calculate_lump_sum(monthly_pension: float, current_age: int, target_age: int) -> float:
    """월연금을 일시금으로 환산한다. employees_service의 일시금 환산 계수(기존 로직)를
    그대로 재사용해 '월연금 x 12 x 잔여연수'에 적용한다."""
    remaining_years = max(target_age - current_age, 0)
    return monthly_pension * 12 * remaining_years * LUMP_SUM_CONVERSION_FACTOR


def simulate_scenarios(
    current_age: int,
    monthly_expenses: float,
    monthly_pension: float,
    asset: float,
    gender: str,
) -> ScenariosResult:
    """정상/조기/일시금/분할 4가지 연금 수령방식을 diagnose_core()에 파라미터만 바꿔
    순차(동기 for 루프)로 실행하고 비교한다. 자산 시뮬레이션 로직은 diagnose_core()에
    전적으로 위임하며, 방식별 monthly_pension/asset 조합만 여기서 계산한다.

    일시금 분기(monthly_pension=0으로 두고 자산에 일시금을 더하는 방식)는
    employees_service.simulate_employees()의 기존 일시금 처리 패턴을 재사용한다.
    """
    target_age = get_target_age(gender)
    lump_sum = _calculate_lump_sum(monthly_pension, current_age, target_age)

    scenario_inputs: dict[ScenarioType, tuple[float, float]] = {
        ScenarioType.NORMAL: (monthly_pension, asset),
        ScenarioType.EARLY: (monthly_pension * (1 - EARLY_REDUCTION_RATE), asset),
        ScenarioType.LUMP_SUM: (0.0, asset + lump_sum),
        ScenarioType.INSTALLMENT: (
            monthly_pension * INSTALLMENT_SPLIT_RATIO,
            asset + lump_sum * INSTALLMENT_SPLIT_RATIO,
        ),
    }

    outcomes: list[ScenarioOutcome] = []
    for scenario_type, (scenario_pension, scenario_asset) in scenario_inputs.items():
        result = diagnose_core(
            current_age=current_age,
            monthly_expenses=monthly_expenses,
            monthly_pension=scenario_pension,
            asset=scenario_asset,
            gender=gender,
        )

        depletion_age = result.depletion_age if result.depletion_age is not None else MAX_AGE
        upfront_lump_sum = scenario_asset - asset  # 초기 자산에 더해진 일시금(있는 경우)
        total_received = sum(point.income for point in result.timeline) + upfront_lump_sum

        outcomes.append(
            ScenarioOutcome(
                scenario_type=scenario_type,
                depletion_age=depletion_age,
                total_received=round(total_received, 2),
                timeline=result.timeline,
            )
        )

    return ScenariosResult(
        current_age=current_age,
        scenarios=outcomes,
        best_scenario=_select_best_scenario(outcomes),
    )


def _select_best_scenario(outcomes: list[ScenarioOutcome]) -> ScenarioType:
    """고갈 나이가 가장 큰 시나리오를 선택하고, 동률이면 총 수령액이 큰 시나리오를 선택한다."""
    best = max(outcomes, key=lambda outcome: (outcome.depletion_age, outcome.total_received))
    return best.scenario_type
