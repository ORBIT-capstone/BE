from app.schemas.retirement import ReadinessStatus, SimulationResult, TimelinePoint

INVESTMENT_RETURN = 0.03  # 자산 운용 수익률
INFLATION_RATE = 0.02  # 물가상승률 (지출/Gap 증가율)
PENSION_GROWTH_RATE = 0.0  # 연금 소득 증가율
MAX_AGE = 100  # 시뮬레이션 상한 나이
TARGET_AGE_MALE = 84  # 남성 목표연령 (통계청 생명표 60세 기대여명 기준)
TARGET_AGE_FEMALE = 88  # 여성 목표연령 (통계청 생명표 60세 기대여명 기준)


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
    """현재 나이부터 MAX_AGE까지 매년 자산 변화를 시뮬레이션"""
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
