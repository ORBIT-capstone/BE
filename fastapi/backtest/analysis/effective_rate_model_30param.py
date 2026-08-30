"""연금 지급률(실효 요율) 보정 모형 — 사학연금공단 실적 데이터로 적합한 경험 모형.

**이 모듈은 법정 산식의 재현이 아니다.** 사학연금공단이 제공한 개인 단위 퇴직급여
마이크로데이터(2020-01~2025-01 퇴직자, A=퇴직연금 40,719건)에서 실제 지급된
연금월액 구간을 재현하도록 계수를 적합한 **경험적 보정 모형**이다. 계수 자체에
법령상 근거가 있는 것이 아니라, 법정 산식 중 우리가 구현할 수 없는 요소들
(보정률, 소득재분배 A/B/C값, 2009년 이전 평균보수월액 기준 별도 산식, 종전규정
유리 원칙)이 실적에 남긴 총합 효과를 관측 가능한 변수로 근사한 것이다.
자세한 근거·한계는 `backtest/reports/calibration_report.md` 참조.

## 왜 단일 상수(기존 PENSION_RATE=1.7%)로는 안 되는가

실적 데이터에서 역산한 실효 지급률(연금월액 / (평균기준소득월액 x 재직연수))은
상수가 아니라 아래 네 축을 따라 체계적으로 움직인다. 기존 엔진의 1.7% 단일 상수는
이 변동을 전혀 반영하지 못해 구간 적중률 43.54%(닫힌구간 20.00%)에 그쳤고,
미적중의 98%가 과대추정이었다.

  1. 재직연수  — 길수록 낮다(10~14년 중앙값 1.49% -> 33년 이상 1.34%). 장기재직자일수록
                 2009년 이전 재직기간(법정 산정기초가 평균보수월액이며 평균기준소득월액보다
                 낮다) 비중이 커지기 때문으로 본다.
  2. 소득수준  — 높을수록 낮다(소득 1분위 1.56% -> 5분위 1.26%). 소득재분배(A값)가
                 실적에 남긴 흔적으로 본다. 연금액이 소득에 완전 비례하지 않는다.
  3. 퇴직연도  — 최근일수록 낮다. 연도별 법정 지급률 인하 스케줄과 방향이 일치한다.
  4. 학교급x직구분 — 집단 간 최대 ±5% 수준의 차이가 남는다.

## 검증

5-fold 교차검증 기준 전체 구간 적중률 80.39%(±0.28), 닫힌구간 78.74%.
집단정보(학교급·직구분) 미제공 시 폴백 프로파일로 78.13%.
`backtest/scripts/phase6_calibrated.py`가 이 수치를 재생산한다.

## 설계상 반드시 지킬 것

- **요율은 재직연수의 연속함수다(계단형 금지).** 구간별 상수표를 쓰면 구간 경계에서
  "1년 더 재직했는데 연금월액이 줄어드는" 역전이 생긴다(실제로 적합 과정에서 관측됐다).
  KNOT_YEARS에서 선형보간하며, 지급액 y x rate(y)가 재직연수에 대해 단조 증가하도록
  적합 단계에서 제약을 걸었다(tests/test_pension_rate_model.py가 이를 고정한다).
- **퇴직연도·퇴직연령 보정항은 관측 범위 밖으로 외삽하지 않는다.** 적합에 쓴 표본은
  2020~2025년 퇴직자뿐이므로 오프셋을 클램프한다. 2030년 퇴직 예정자도 2025년과
  동일하게 취급된다 — 법정 지급률 인하 스케줄을 미래로 연장 적용하지 **않는다**는
  뜻이며, 이는 데이터가 뒷받침하지 않는 외삽을 피하려는 의도적 선택이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "JobType",
    "SchoolLevel",
    "effective_pension_rate",
]


class SchoolLevel(str, Enum):
    """학교급. 원천 데이터의 `학교급` 컬럼 범주와 1:1 대응한다."""

    KINDERGARTEN = "kindergarten"  # 유치원
    ELEMENTARY = "elementary"  # 초등학교
    MIDDLE = "middle"  # 중학교
    HIGH = "high"  # 고등학교
    SPECIAL = "special"  # 특수학교
    JUNIOR_COLLEGE = "junior_college"  # 전문대학
    UNIVERSITY = "university"  # 대학교
    CORPORATION = "corporation"  # 법인


class JobType(str, Enum):
    """직구분. 원천 데이터의 `직구분` 컬럼 범주와 1:1 대응한다."""

    TEACHER = "teacher"  # 교원
    STAFF = "staff"  # 직원


# 보정항의 기준점. 이 값에서 각 보정항의 기여가 0이 된다(요율 = KNOT_RATES 보간값).
REFERENCE_INCOME = 5_000_000.0  # 기준 평균기준소득월액 (원)
REFERENCE_RETIRE_YEAR = 2022  # 적합 표본(2020~2025)의 중앙 연도
REFERENCE_RETIRE_AGE = 60

# 관측 범위 밖 외삽 차단용 클램프. 적합 표본은 퇴직연도 2020~2025,
# 퇴직당시연령은 대부분 45~68세 구간에 있다.
RETIRE_YEAR_OFFSET_RANGE = (-2, 3)
RETIRE_AGE_OFFSET_RANGE = (-15, 8)

# 산출 요율의 방어적 상·하한. 어떤 입력 조합에서도 이 범위를 벗어나지 않는다.
RATE_FLOOR = 0.010
RATE_CEILING = 0.022

# 요율 곡선의 매듭(재직연수). KNOT_RATES와 길이가 같아야 한다.
KNOT_YEARS: tuple[float, ...] = (10.0, 13.0, 16.0, 19.0, 22.0, 25.0, 28.0, 30.0, 31.5, 33.0, 34.5, 36.0)


@dataclass(frozen=True)
class RateProfile:
    """적합된 계수 묶음.

    group_multipliers가 비어 있으면 집단 보정을 쓰지 않는 폴백 프로파일이다.
    두 프로파일은 각각 독립적으로 적합했다 — WITH_GROUP의 계수에 집단배수만
    1.0으로 두고 쓰면 안 된다(그 조합의 적중률은 76.2%로 폴백 프로파일보다 낮다).
    """

    knot_rates: tuple[float, ...]
    income_elasticity: float
    retire_year_coef: float
    retire_age_coef: float
    group_multipliers: dict[tuple[SchoolLevel, JobType], float]

    def __post_init__(self) -> None:
        if len(self.knot_rates) != len(KNOT_YEARS):
            raise ValueError(
                f"knot_rates 길이({len(self.knot_rates)})가 KNOT_YEARS 길이({len(KNOT_YEARS)})와 다릅니다."
            )


# 학교급x직구분 집단배수. 표본이 작은 집단이 과적합되지 않도록 표본수 기반
# 축소(shrinkage, n/(n+300))를 적용한 값이다 — 원시 적합값이 아니다.
# 원천 데이터에 존재하지 않는 조합(예: 법인x교원)은 여기 없으며, 그런 입력은
# 집단 보정 없이 폴백 프로파일로 처리된다.
_GROUP_MULTIPLIERS: dict[tuple[SchoolLevel, JobType], float] = {
    (SchoolLevel.HIGH, JobType.TEACHER): 0.9974,
    (SchoolLevel.HIGH, JobType.STAFF): 0.9805,
    (SchoolLevel.UNIVERSITY, JobType.TEACHER): 1.0473,
    (SchoolLevel.UNIVERSITY, JobType.STAFF): 0.9529,
    (SchoolLevel.CORPORATION, JobType.STAFF): 0.9968,
    (SchoolLevel.KINDERGARTEN, JobType.TEACHER): 1.0501,
    (SchoolLevel.KINDERGARTEN, JobType.STAFF): 0.9736,
    (SchoolLevel.JUNIOR_COLLEGE, JobType.TEACHER): 1.0493,
    (SchoolLevel.JUNIOR_COLLEGE, JobType.STAFF): 0.9613,
    (SchoolLevel.MIDDLE, JobType.TEACHER): 1.0073,
    (SchoolLevel.MIDDLE, JobType.STAFF): 0.9776,
    (SchoolLevel.ELEMENTARY, JobType.TEACHER): 0.9944,
    (SchoolLevel.ELEMENTARY, JobType.STAFF): 0.9908,
    (SchoolLevel.SPECIAL, JobType.TEACHER): 1.0073,
    (SchoolLevel.SPECIAL, JobType.STAFF): 0.9744,
}

# 학교급·직구분을 아는 경우. 5-fold CV 전체 80.39% / 닫힌구간 78.74%.
WITH_GROUP = RateProfile(
    knot_rates=(
        0.015160, 0.015251, 0.015419, 0.015714, 0.015552, 0.015150,
        0.014964, 0.014753, 0.014836, 0.014890, 0.015000, 0.015000,
    ),
    income_elasticity=0.200,
    retire_year_coef=-0.0140,
    retire_age_coef=0.00550,
    group_multipliers=_GROUP_MULTIPLIERS,
)

# 학교급·직구분을 모르는 경우(기존 API 클라이언트 포함). 5-fold CV 전체 78.13%.
WITHOUT_GROUP = RateProfile(
    knot_rates=(
        0.015840, 0.015903, 0.015874, 0.016185, 0.016041, 0.015207,
        0.015293, 0.014876, 0.014766, 0.014869, 0.015000, 0.015000,
    ),
    income_elasticity=0.200,
    retire_year_coef=-0.0140,
    retire_age_coef=0.00700,
    group_multipliers={},
)


def _interpolate_knot_rate(service_years: float, knot_rates: tuple[float, ...]) -> float:
    """KNOT_YEARS 위에서 선형보간한다(양 끝 밖은 끝값으로 고정).

    numpy.interp와 동작이 같다 — 서비스 계층에 numpy 의존을 들이지 않으려고
    직접 구현했다(백테스트 스크립트는 numpy.interp를 쓰며 두 결과가 일치하는지
    tests/test_pension_rate_model.py에서 확인한다).
    """
    if service_years <= KNOT_YEARS[0]:
        return knot_rates[0]
    if service_years >= KNOT_YEARS[-1]:
        return knot_rates[-1]
    for i in range(1, len(KNOT_YEARS)):
        right = KNOT_YEARS[i]
        if service_years <= right:
            left = KNOT_YEARS[i - 1]
            weight = (service_years - left) / (right - left)
            return knot_rates[i - 1] + (knot_rates[i] - knot_rates[i - 1]) * weight
    raise AssertionError("도달 불가 — 위 두 경계 검사가 모든 입력을 덮는다.")


def _select_profile(
    school_level: SchoolLevel | None, job_type: JobType | None
) -> tuple[RateProfile, float]:
    """(프로파일, 집단배수)를 고른다.

    학교급·직구분이 둘 다 주어졌고 그 조합이 적합 표본에 존재할 때만 WITH_GROUP을
    쓴다. 조합이 표본에 없으면(예: 법인x교원) 집단배수를 1.0으로 둔 WITH_GROUP이
    아니라 WITHOUT_GROUP으로 간다 — 두 프로파일의 나머지 계수가 서로 다르게
    적합됐기 때문이다.
    """
    if school_level is None or job_type is None:
        return WITHOUT_GROUP, 1.0
    multiplier = WITH_GROUP.group_multipliers.get((school_level, job_type))
    if multiplier is None:
        return WITHOUT_GROUP, 1.0
    return WITH_GROUP, multiplier


def effective_pension_rate(
    service_years: float,
    base_income: float,
    *,
    retire_year: int | None = None,
    retire_age: int | None = None,
    school_level: SchoolLevel | None = None,
    job_type: JobType | None = None,
) -> float:
    """재직연수 1년당 실효 연금 지급률을 반환한다.

    연금월액 = base_income x 재직연수 x effective_pension_rate(...) 로 쓴다.

    Args:
        service_years: 연금 산정에 쓰는 재직연수(법정 상한 적용 후). 요율 구간을 고른다.
        base_income: 평균기준소득월액(원). 소득 보정항의 입력이다.
        retire_year: 퇴직 연도. None이면 보정 없음(기준연도 취급).
        retire_age: 퇴직 당시 나이. None이면 보정 없음(기준연령 취급).
        school_level, job_type: 둘 다 주어지고 조합이 표본에 있을 때만 집단 보정을 적용한다.

    base_income이 0 이하이면 소득 보정항을 계산할 수 없으므로 기준소득으로 간주해
    보정 없이(비율 1.0) 처리한다 — 호출자가 이미 검증한 값을 다시 예외로 만들지 않는다.
    """
    profile, group_multiplier = _select_profile(school_level, job_type)

    rate = _interpolate_knot_rate(service_years, profile.knot_rates)

    income_ratio = base_income / REFERENCE_INCOME if base_income > 0 else 1.0
    rate *= income_ratio ** (-profile.income_elasticity)

    year_offset = 0 if retire_year is None else _clamp(
        retire_year - REFERENCE_RETIRE_YEAR, *RETIRE_YEAR_OFFSET_RANGE
    )
    age_offset = 0 if retire_age is None else _clamp(
        retire_age - REFERENCE_RETIRE_AGE, *RETIRE_AGE_OFFSET_RANGE
    )
    rate *= 1 + profile.retire_year_coef * year_offset + profile.retire_age_coef * age_offset

    rate *= group_multiplier

    return _clamp(rate, RATE_FLOOR, RATE_CEILING)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
