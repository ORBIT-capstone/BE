"""B(조기퇴직연금)·C(퇴직연금공제일시금) 정성 점검 (Phase 5).

정량 검증은 하지 않는다:
  - B: 법정 지급개시연령 유예 스케줄을 확보하지 못해 실제 미달연수를 계산할 수 없다.
    동일 재직연수 구간 x 동일 퇴직연도 안에서 A(정상)와 B(조기)의 정답 구간(연금월액_구분)
    분포 차이만 기술 통계로 확인한다.
  - C: 실제 선택된 공제연수가 데이터에 없어 역산 검증이 불가능하다. 현재 엔진의 클램프
    기본값 min(26, 재직연수-10)을 이 데이터의 실제 재직연수 분포에 적용했을 때의 분포만
    기술 통계로 확인한다(진위 검증이 아니라 클램프가 얼마나 자주 걸리는지 확인).

M1: 연금월액_구분==0("해당 금액 없음")은 채점/기술통계 대상이 아니므로 A/B 비교에서
제외한다(제외 행수를 리포트에 기록).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = BACKTEST_DIR.parent
sys.path.insert(0, str(FASTAPI_ROOT))

from app.services.retirement_service import (  # noqa: E402
    EARLY_REDUCTION_RATE_PER_YEAR,
    EARLY_YEARS_MAX,
    MAX_DEDUCTION_YEARS,
    MIN_PENSION_YEARS,
)

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"

MIN_CELL = 5

# L1: 하한/상한을 +-inf로 열어 범위 밖 값이 NaN이 되어 groupby에서 조용히 사라지지
# 않도록 한다(아래 assertion으로 재확인).
TENURE_BINS = [-float("inf"), 10, 15, 20, 25, 30, 33, 34.0001, float("inf")]
TENURE_LABELS = ["<10", "10~14", "15~19", "20~24", "25~29", "30~32", "33~34", "34+"]


def _bin_tenure(s: pd.Series) -> pd.Series:
    return pd.cut(s, bins=TENURE_BINS, right=False, labels=TENURE_LABELS)


def compare_ab_distribution(df: pd.DataFrame) -> list[str]:
    a_all = df[df["급여종류"] == "퇴직연금"].copy()
    b_all = df[df["급여종류"] == "조기퇴직연금"].copy()

    # M1: 정답구간 없음(코드0) 행은 기술통계 대상이 아니므로 제외
    n_a_excluded = int((a_all["연금월액_구분"] == 0).sum())
    n_b_excluded = int((b_all["연금월액_구분"] == 0).sum())
    a = a_all[a_all["연금월액_구분"] != 0].copy()
    b = b_all[b_all["연금월액_구분"] != 0].copy()

    a["재직연수_구간"] = _bin_tenure(a["재직연수"])
    b["재직연수_구간"] = _bin_tenure(b["재직연수"])
    a["퇴직연도"] = a["퇴직연월"] // 100
    b["퇴직연도"] = b["퇴직연월"] // 100

    # L1: pd.cut 범위 밖 값이 조용히 사라지지 않았는지 확인
    a_covered = int(a.groupby("재직연수_구간", observed=True).size().sum())
    b_covered = int(b.groupby("재직연수_구간", observed=True).size().sum())
    assert a_covered == len(a), f"A 재직연수_구간 구간화에서 {len(a) - a_covered}행 누락"
    assert b_covered == len(b), f"B 재직연수_구간 구간화에서 {len(b) - b_covered}행 누락"

    lines = [
        "## B(조기퇴직연금) vs A(정상 퇴직연금) — 동일 재직연수구간x퇴직연도 내 정답구간(연금월액_구분) 분포",
        "",
        "정량 검증 보류 사유: 법정 지급개시연령 유예 스케줄 미확보로 실제 미달연수(조기수령 연수)를 "
        "계산할 수 없다. 아래는 두 그룹 모두 n>=5인 셀만 기술 통계로 비교한다(n<5 셀은 마스킹).",
        "",
        f"정답구간 없음(연금월액_구분==0, 채점 대상 아님) 제외: A {n_a_excluded}행, B {n_b_excluded}행.",
        "",
    ]

    rows = []
    for (tenure, year), b_sub in b.groupby(["재직연수_구간", "퇴직연도"], observed=True):
        if len(b_sub) < MIN_CELL:
            continue
        a_sub = a[(a["재직연수_구간"] == tenure) & (a["퇴직연도"] == year)]
        if len(a_sub) < MIN_CELL:
            continue
        a_mode = a_sub["연금월액_구분"].mode()
        b_mode = b_sub["연금월액_구분"].mode()
        rows.append(
            {
                "재직연수구간": tenure,
                "퇴직연도": year,
                "A n": len(a_sub),
                "B n": len(b_sub),
                "A 최빈 구간코드": int(a_mode.iloc[0]) if not a_mode.empty else None,
                "B 최빈 구간코드": int(b_mode.iloc[0]) if not b_mode.empty else None,
                "A 평균구간코드": round(a_sub["연금월액_구분"].mean(), 2),
                "B 평균구간코드": round(b_sub["연금월액_구분"].mean(), 2),
            }
        )

    if not rows:
        lines.append("두 그룹 모두 n>=5인 (재직연수구간 x 퇴직연도) 셀이 없어 비교 불가.")
    else:
        table = pd.DataFrame(rows)
        lines.append(table.to_markdown(index=False))
        lower_count = (table["B 평균구간코드"] < table["A 평균구간코드"]).sum()
        lines.append("")
        lines.append(
            f"비교 가능 셀 {len(table)}개 중 B의 평균 구간코드가 A보다 낮은(=금액이 낮은 구간에 몰린) "
            f"셀: {lower_count}개."
        )

    lines.append("")
    lines.append(
        f"**[해결됨] 정정 및 조치**: 이전 버전은 조기수령 감액을 "
        f"`monthly_pension * (1 - {EARLY_REDUCTION_RATE_PER_YEAR} * early_years)` 연속식으로 계산했다. "
        "**정정**: 애초 서술('계단식 로직 부재')이 부정확했다 — `early_years`가 정수일 때 이 식은 "
        "법정 계단식 감액률(1년 이내 95%, 1년 초과~2년 이내 90%, 2년 초과~3년 이내 85%, "
        "3년 초과~4년 이내 80%, 4년 초과~5년 이내 75%)과 수치가 완전히 일치했다 — 계단 로직 자체가 "
        "없었던 게 아니라, 소수 미달연수(예: 1.5년)를 입력하면 계단이 아니라 선형으로 처리돼 "
        "실제 법정 감액률보다 작게 감액되는 문제였다. 정확한 원인은 '소수 미달연수 미대응 + "
        "미달연수 정합성 검증 부재'다: 미달연수(지급개시연령까지 남은 기간)를 계산해 `early_years`로 "
        "변환하는 로직이 엔진 밖(API 호출자)에 있었고, 그 변환값이 올바른지 엔진이 검증할 수 없었다. "
        "**조치**: `_early_reduction_rate()`가 `EARLY_REDUCTION_RATE_PER_YEAR * ceil(early_years)`로 "
        "계단식을 명시적으로 구현했다(정수 입력 시 결과 동일 — 회귀 테스트로 고정). "
        "미달연수를 지급개시연령으로부터 서버가 직접 산정하는 기능은 여전히 스코프 밖이다 — "
        "지급개시연령 유예 스케줄 확보 후 별도 이슈로 진행(scope_limitations.md 향후 과제 참조)."
    )
    lines.append("")
    return lines


def _clamp_conclusion_sentence(binding: int, n: int) -> str:
    """binding 비율에 따라 결론 문장을 분기한다 — 하드코딩된 단정 문구로 인한
    자기모순(예: 0.0%인데 "자주 작동한다")을 막는다. engine_defects.md와 서술이
    충돌하면 engine_defects.md의 "사실상 죽은 코드" 쪽을 정본으로 삼는다.
    """
    ratio = binding / n * 100
    if binding == 0:
        return (
            f"**관찰 기록**: C 표본에서 {MAX_DEDUCTION_YEARS}년 클램프가 걸리는 행은 0건(0.00%)이다. "
            "이 데이터 범위 안에서는 클램프가 사실상 죽은 코드(dead branch)로 작동한다 — "
            "결함이 아니라 관찰이다. 실제 선택 공제연수 데이터가 없어 이 기본값 자체가 데이터와 "
            "'맞는지'는 판정할 수 없다 — scope_limitations.md에 검증 불가 항목으로 기록한다."
        )
    if ratio < 5:
        qualifier = "드물게"
    else:
        qualifier = "자주"
    return (
        f"**결함 후보 기록**: C 표본의 {ratio:.1f}%({binding:,}/{n:,}행)가 클램프 상한"
        f"({MAX_DEDUCTION_YEARS}년)에 걸리는 재직연수 구간에 속해, 클램프가 {qualifier} "
        "작동한다. 실제 선택 공제연수 데이터가 없어 이 기본값이 데이터와 '맞는지'는 판정할 수 "
        "없다 — scope_limitations.md에 검증 불가 항목으로 기록한다."
    )


def deduction_years_clamp_check(df: pd.DataFrame) -> list[str]:
    c = df[df["급여종류"] == "퇴직연금공제일시금"].copy()
    n = len(c)

    header = [
        "## C(퇴직연금공제일시금) — 공제연수 클램프 기본값 기술 통계",
        "",
        f"현재 엔진 기본값: `min({MAX_DEDUCTION_YEARS}, 재직연수 - {MIN_PENSION_YEARS})` "
        "(retirement_service.py::_resolve_split_deduction_years, deduction_years 미지정 시).",
        "",
        "정량 검증 보류 사유: 실제로 선택된 공제연수는 데이터에 없어(연금월액·일시금금액 두 구간코드만 "
        "존재) 역산 검증이 불가능하다. 아래는 이 데이터의 실제 재직연수 분포에 클램프 기본값을 "
        "그대로 적용했을 때의 분포만 기술한다 — 실제 선택값과의 일치 여부를 판정하는 것이 아니다.",
        "",
    ]

    # M3: 0으로 나누기 가드
    if n == 0:
        return header + ["C 표본이 없어(n=0) 기술 통계를 낼 수 없다.", ""]

    raw_deduction = c["재직연수"] - MIN_PENSION_YEARS
    clamped = raw_deduction.clip(upper=MAX_DEDUCTION_YEARS)
    binding = int((raw_deduction > MAX_DEDUCTION_YEARS).sum())

    # M3: MIN_CELL 셀 억제 — n<5면 개별 레코드가 그대로 드러날 수 있는 min/분위 통계를 마스킹
    if n < MIN_CELL:
        stats_line = f"- C 표본 수: n<{MIN_CELL} (마스킹 — 분위 통계 생략)"
        binding_line = f"- {MAX_DEDUCTION_YEARS}년 상한 적용(클램프 후) 행 비율: n<{MIN_CELL} (마스킹)"
        conclusion = (
            f"**관찰 기록**: C 표본 크기가 {MIN_CELL} 미만이라 분포 통계를 마스킹했다. "
            "결론을 내리기에 표본이 너무 작다 — scope_limitations.md에 검증 불가 항목으로 기록한다."
        )
    else:
        # L2: 리포트 문구("클램프 기본값을 그대로 적용했을 때의 분포")대로 clamped 값을 보고한다.
        stats_line = (
            f"- C 표본 수: {n:,}\n"
            f"- `min({MAX_DEDUCTION_YEARS}, 재직연수 - {MIN_PENSION_YEARS})` (클램프 적용 후) 분위: "
            f"min={clamped.min():.2f}, p25={clamped.quantile(.25):.2f}, "
            f"median={clamped.median():.2f}, p75={clamped.quantile(.75):.2f}, "
            f"max={clamped.max():.2f} (년)"
        )
        binding_line = (
            f"- {MAX_DEDUCTION_YEARS}년 상한이 실제로 걸리는(재직연수-{MIN_PENSION_YEARS} > "
            f"{MAX_DEDUCTION_YEARS}) 행 비율: {binding / n * 100:.2f}% ({binding:,}/{n:,})"
        )
        conclusion = _clamp_conclusion_sentence(binding, n)

    return header + [stats_line, binding_line, "", conclusion, ""]


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)

    lines = ["# Phase 5 — 조기연금·공제일시금 정성 점검", ""]
    lines.append(
        "데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/). "
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 출력하지 않는다 — 구간 코드(1~8)와 그 평균/최빈값만 사용한다."
    )
    lines.append("")
    lines += compare_ab_distribution(df)
    lines += deduction_years_clamp_check(df)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase5_qualitative.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
