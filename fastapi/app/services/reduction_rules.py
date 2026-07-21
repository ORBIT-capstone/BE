from dataclasses import dataclass


@dataclass(frozen=True)
class RateBracket:
    """초과소득월액 구간별 감액 산식.

    구간은 (이전 구간의 upper_bound, 이 구간의 upper_bound] 범위를 의미하며,
    감액액 = base_amount + (초과소득월액 - 이전 구간 upper_bound) * rate 로 계산한다.
    """

    upper_bound: float | None  # 구간 상한 (만원). 마지막 구간은 None(무제한)
    base_amount: float  # 구간 시작 지점까지의 누적 감액액 (만원)
    rate: float  # 구간 내 초과소득월액에 적용되는 감액률


@dataclass(frozen=True)
class ReductionRule:
    """연도별 국민연금 소득심사(재직자 노령연금 감액) 규칙"""

    year: int  # 적용 연도
    threshold: float  # 감액 기준 월소득액 A값 (만원). 이 금액을 초과해야 감액 발생
    rate_brackets: list[RateBracket]  # 초과소득월액 구간별 감액 산식 (upper_bound 오름차순)


# 초과소득월액 구간별 감액률 구조는 수년간 동일하게 유지되어 왔으므로 규칙 간 공유한다.
_STANDARD_RATE_BRACKETS: list[RateBracket] = [
    RateBracket(upper_bound=100, base_amount=0, rate=0.05),
    RateBracket(upper_bound=200, base_amount=5, rate=0.10),
    RateBracket(upper_bound=300, base_amount=15, rate=0.15),
    RateBracket(upper_bound=400, base_amount=30, rate=0.20),
    RateBracket(upper_bound=None, base_amount=50, rate=0.25),
]

# threshold(A값)는 매년 새로 발표되는 통계 수치이므로, 새 연도가 공지되면
# 코드 변경 없이 이 목록에 ReductionRule 항목만 추가하면 된다.
REDUCTION_RULES: list[ReductionRule] = [
    ReductionRule(year=2023, threshold=286.1, rate_brackets=_STANDARD_RATE_BRACKETS),
    ReductionRule(year=2024, threshold=298.9, rate_brackets=_STANDARD_RATE_BRACKETS),
    ReductionRule(year=2025, threshold=309.7, rate_brackets=_STANDARD_RATE_BRACKETS),
]


def get_reduction_rule(year: int | None = None) -> ReductionRule:
    """적용할 감액 규칙을 반환한다.

    year가 None이면 등록된 규칙 중 가장 최근 연도를 사용하고,
    등록된 규칙보다 이전 연도가 주어지면 가장 오래된 규칙으로 대체한다(하한 방어).
    """
    if not REDUCTION_RULES:
        raise ValueError("등록된 감액 규칙이 없습니다.")

    sorted_rules = sorted(REDUCTION_RULES, key=lambda rule: rule.year)

    if year is None:
        return sorted_rules[-1]

    applicable = [rule for rule in sorted_rules if rule.year <= year]
    return applicable[-1] if applicable else sorted_rules[0]


def calculate_bracket_reduction(excess_income: float, rate_brackets: list[RateBracket]) -> float:
    """초과소득월액에 구간별 감액 산식을 적용해 감액액을 계산한다."""
    if excess_income <= 0:
        return 0.0

    lower_bound = 0.0
    for bracket in rate_brackets:
        if bracket.upper_bound is None or excess_income <= bracket.upper_bound:
            return bracket.base_amount + (excess_income - lower_bound) * bracket.rate
        lower_bound = bracket.upper_bound

    raise ValueError("초과소득월액에 해당하는 구간을 찾을 수 없습니다.")
