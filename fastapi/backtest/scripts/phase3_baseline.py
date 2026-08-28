"""현재 엔진 baseline 구간 적중률 측정 (Phase 3, A: 정상 퇴직연금).

fastapi/app/services/employees_service.py 의 실제 산식(PENSION_RATE 상수, 재직연수
상한 캡 로직)을 그대로 재사용해 예측값을 만든다. 상수를 다시 타이핑하지 않고
모듈에서 직접 import한다.

주의: 프로덕션 REST 엔드포인트(/api/employees/simulate)는 SimulateRequest.current_years가
정수(int) 필드라 연 단위 미만 정밀도가 손실된다. 이는 API 입력 스키마의 제약이지
산식 자체(연산은 retire_months/12로 이미 소수 재직연수를 지원)의 제약이 아니므로,
백테스트에서는 정수 월 단위로 정밀한 실제 재직월수를 그대로 사용해 산식 핵심 로직만
재현한다. PENSION_RATE 상수와 재직연수 상한(36) 캡 로직은 employees_service.py의
소스를 그대로 따른다 (아래 predict_monthly_pension 함수 docstring 참조).

적중 판정: 연금월액_하한 <= predicted < 연금월액_상한 (원 단위, Phase 1 정제 데이터셋 기준)

연금월액_구분==0("해당 금액 없음")인 행은 채점 대상이 아니므로 적중/미적중/과대/과소
어디에도 넣지 않고 분모에서 제외한다(제외 행수는 리포트에 별도 기록).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKTEST_DIR / "scripts"))

from engine_baseline import (  # noqa: E402
    LEGACY_PENSION_RATE,
    LEGACY_SERVICE_YEARS_CAP,
    PENSION_ELIGIBILITY_MONTHS,
    predict_monthly_pension_legacy,
)
from interval_utils import is_hit  # noqa: E402

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"

MIN_CELL = 5  # n < 5 그룹은 마스킹


def _mask_rate(hit: pd.Series) -> tuple[str, int]:
    n = len(hit)
    if n < MIN_CELL:
        return "n<5 (마스킹)", n
    return f"{hit.mean() * 100:.2f}%", n


def _direction_rates(df: pd.DataFrame) -> tuple[str, str]:
    """미적중 행 중 과대추정/과소추정 비율.

    호출 시점에 이미 연금월액_구분==0(정답 없음) 행이 제외돼 있어야 한다 — 그래야
    모든 미적중 행이 과대 또는 과소 둘 중 하나로 분류되어 두 비율의 합이 100%가 된다.
    """
    miss = df[~df["hit"]]
    n_miss = len(miss)
    if n_miss < MIN_CELL:
        return "n<5 (마스킹)", "n<5 (마스킹)"
    over = int((miss["predicted"] >= miss["연금월액_상한"]).sum())
    under = int((miss["predicted"] < miss["연금월액_하한"]).sum())
    assert over + under == n_miss, (
        f"과대+과소({over + under}) != 미적중 행수({n_miss}) — 정답구간 없음(코드0) 행이 "
        "섞여 있지 않은지 확인 필요"
    )
    return f"{over / n_miss * 100:.2f}%", f"{under / n_miss * 100:.2f}%"


def build_breakdown(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    covered = 0
    for key, sub in df.groupby(group_col, observed=True):
        covered += len(sub)
        rate, n = _mask_rate(sub["hit"])
        over_rate, under_rate = _direction_rates(sub)
        rows.append({group_col: key, "n": n if n >= MIN_CELL else f"<{MIN_CELL}", "적중률": rate, "과대추정률(미적중중)": over_rate, "과소추정률(미적중중)": under_rate})
    assert covered == len(df), (
        f"{group_col} 구간화에서 {len(df) - covered}행이 그룹 밖으로 누락됨 "
        "(pd.cut 범위 밖 값이 NaN이 되어 groupby에서 조용히 빠졌을 가능성)"
    )
    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)
    a_all = df[df["급여종류"] == "퇴직연금"].copy()
    n_missing_income = int(a_all["평균기준소득월액"].isna().sum())
    a_with_income = a_all[a_all["평균기준소득월액"].notna()].copy()

    # M1: 연금월액_구분==0("해당 금액 없음")은 채점 대상이 아니다 — 적중/미적중/과대/과소
    # 어디에도 넣지 않고 분모에서 제외한다. 제외 행수는 리포트에 별도로 기록한다.
    n_no_answer = int((a_with_income["연금월액_구분"] == 0).sum())
    a = a_with_income[a_with_income["연금월액_구분"] != 0].copy()

    a["predicted"] = [
        predict_monthly_pension_legacy(income, months)
        for income, months in zip(a["평균기준소득월액"], a["재직월수"])
    ]
    a["hit"] = is_hit(a["predicted"], a["연금월액_하한"], a["연금월액_상한"])

    overall_rate, n_all = _mask_rate(a["hit"])
    closed = a[a["연금월액_구분"].between(1, 7)]
    closed_rate, n_closed = _mask_rate(closed["hit"])
    open_top = a[a["연금월액_구분"] == 8]
    open_rate, n_open = _mask_rate(open_top["hit"])
    over_all, under_all = _direction_rates(a)

    # L1: 하한/상한을 +-inf로 열어 범위 밖 값이 NaN이 되어 groupby에서 조용히
    # 사라지지 않도록 한다(build_breakdown의 covered==len(df) assertion으로 재확인).
    a["재직연수_구간"] = pd.cut(
        a["재직연수"], bins=[-float("inf"), 10, 15, 20, 25, 30, 33, 34.0001, float("inf")], right=False,
        labels=["<10", "10~14", "15~19", "20~24", "25~29", "30~32", "33~34", "34+"],
    )
    a["퇴직연도"] = a["퇴직연월"] // 100
    a["퇴직당시연령_구간"] = pd.cut(
        a["퇴직당시연령"], bins=[-float("inf"), 50, 55, 60, 65, float("inf")], right=False,
        labels=["~49", "50~54", "55~59", "60~64", "65+"],
    )
    a["학교급_직구분"] = a["학교급"].astype(str) + "×" + a["직구분"].astype(str)

    by_years = build_breakdown(a, "재직연수_구간")
    by_retire_year = build_breakdown(a, "퇴직연도")
    by_age = build_breakdown(a, "퇴직당시연령_구간")
    by_school_job = build_breakdown(a, "학교급_직구분")

    lines: list[str] = []
    lines.append("# Baseline Report — Phase 3 (A: 정상 퇴직연금)")
    lines.append("")
    lines.append("데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).")
    lines.append(
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 이 리포트 어디에도 없다 — 구간 코드와 적중률만 기록한다."
    )
    lines.append("")
    lines.append(
        f"예측식: **개선 전** 엔진 산식(단일 지급률 {LEGACY_PENSION_RATE}, 재직연수 상한 "
        f"{LEGACY_SERVICE_YEARS_CAP}년 일괄 캡, 최소가입월수 {PENSION_ELIGIBILITY_MONTHS}개월). "
        "이 리포트는 개선 전 상태를 고정 기록하는 것이므로, 프로덕션 코드를 import하지 않고 "
        "`backtest/scripts/engine_baseline.py`에 동결한 legacy 상수를 쓴다 — 프로덕션이 "
        "바뀌어도 이 수치는 변하지 않아야 하기 때문이다. **개선 후 수치는 "
        "`calibration_report.md`를 볼 것.**"
    )
    lines.append("")
    lines.append("## 전체 지표")
    lines.append("")
    lines.append(
        f"- 표본 수(A. 퇴직연금): {n_all:,} (원본 {len(a_all):,}행 중 평균기준소득월액 결측 "
        f"{n_missing_income}행, 정답구간 없음(연금월액_구분==0, 채점 대상 아님) {n_no_answer}행 제외)"
    )
    lines.append(f"- 전체 적중률: {overall_rate}")
    lines.append(f"- 닫힌 구간(코드 1~7) 적중률: {closed_rate} (n={n_closed:,})")
    lines.append(
        f"- 최상단 개방구간(코드 8) 적중률: {open_rate} (n={n_open:,}) — "
        "**주의**: 코드 8은 상한이 np.inf라 predicted가 아무리 과대추정돼도 무조건 적중으로 잡힌다. "
        "이 수치를 정확도로 해석하지 말 것."
    )
    lines.append(f"- 전체 미적중 중 과대추정 비율: {over_all}")
    lines.append(f"- 전체 미적중 중 과소추정 비율: {under_all}")
    lines.append("")
    lines.append("## 재직연수 구간별 적중률")
    lines.append("")
    lines.append(by_years.to_markdown(index=False))
    lines.append("")
    lines.append("## 퇴직연도별 적중률")
    lines.append("")
    lines.append(by_retire_year.to_markdown(index=False))
    lines.append("")
    lines.append("## 퇴직당시연령 구간별 적중률")
    lines.append("")
    lines.append(by_age.to_markdown(index=False))
    lines.append("")
    lines.append("## 학교급×직구분별 적중률")
    lines.append("")
    lines.append(by_school_job.to_markdown(index=False))
    lines.append("")
    lines.append("## 재직기간 상한 처리 여부 (엔진 결함 후보)")
    lines.append("")
    lines.append(
        "`employees_service.py`의 `simulate_employees`는 `pension_years = min(retire_months / 12, 36)`으로 "
        "재직연수 상한을 **일괄 36년**으로 캡한다. 이는 결함이다 — 사학연금법 부칙(법률 제13561호)에 따르면 "
        "2016.1.1 시점 재직기간에 따라 상한이 33/34/35/36년으로 차등 적용된다(2016.1.1 이후 임용자만 36년 상한). "
        "단순 36년 일괄 캡은 2016.1.1 이전부터 재직한 장기재직자의 연금월액을 과대추정한다. "
        "상세는 `engine_defects.md` 참조. **이번 트랙에서는 코드를 수정하지 않는다.**"
    )
    lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "baseline_report.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
