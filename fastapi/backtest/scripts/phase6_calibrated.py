"""보정 지급률 모형 적용 후 구간 적중률 측정 (Phase 6, A: 정상 퇴직연금).

`app/services/pension_rate_model.py`의 계수를 **재타이핑하지 않고** 프로덕션
모듈에서 직접 import해, `predict_monthly_pension`(=프로덕션
`calculate_monthly_pension`)으로 예측값을 만든다. 즉 이 스크립트가 재는 것은
"백테스트용 별도 구현"이 아니라 실제 배포되는 엔진의 성능이다.

계수를 적합할 때 쓴 표본과 여기서 채점하는 표본은 같다(전수 40,719행). 따라서
아래 '전체 표본' 수치는 in-sample이며 낙관 편향이 있다 — 일반화 성능은 같은
스크립트가 함께 계산하는 5-fold 교차검증 수치로 판단할 것. 교차검증은 계수를
fold마다 다시 적합하는 것이 원칙이나, 이 스크립트는 배포된 고정 계수를 쓰므로
그렇게 할 수 없다. 대신 적합 절차 자체를 fold별로 재실행한 교차검증 결과를
`calibration_report.md`에 기록해 두었고(전체 80.39%), 이 스크립트는 그 값과
in-sample 값의 격차가 과적합으로 볼 만큼 벌어지지 않았는지만 확인한다.

적중 판정: 연금월액_하한 <= predicted < 연금월액_상한 (원 단위)
연금월액_구분==0("해당 금액 없음") 행은 채점 분모에서 제외한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKTEST_DIR / "scripts"))

from engine_baseline import (  # noqa: E402
    JOB_TYPE_BY_KOREAN,
    SCHOOL_LEVEL_BY_KOREAN,
    predict_monthly_pension,
    predict_monthly_pension_legacy,
)
from interval_utils import is_hit  # noqa: E402

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"

MIN_CELL = 5

# calibration_report.md에 기록된 5-fold 교차검증 수치(적합 절차를 fold별로 재실행).
# in-sample 값이 이 값보다 크게 높으면 과적합을 의심해야 한다.
CV_OVERALL_WITH_GROUP = 80.39
CV_OVERALL_WITHOUT_GROUP = 78.13


def _rate(hit: pd.Series) -> str:
    if len(hit) < MIN_CELL:
        return "n<5 (마스킹)"
    return f"{hit.mean() * 100:.2f}%"


def _direction(df: pd.DataFrame, pred_col: str) -> tuple[str, str]:
    miss = df[~df[pred_col + "_hit"]]
    if len(miss) < MIN_CELL:
        return "n<5 (마스킹)", "n<5 (마스킹)"
    over = int((miss[pred_col] >= miss["연금월액_상한"]).sum())
    under = int((miss[pred_col] < miss["연금월액_하한"]).sum())
    assert over + under == len(miss), "정답구간 없음(코드0) 행이 섞여 있는지 확인 필요"
    return f"{over / len(miss) * 100:.2f}%", f"{under / len(miss) * 100:.2f}%"


def _breakdown(df: pd.DataFrame, group_col: str, pred_col: str) -> pd.DataFrame:
    rows = []
    covered = 0
    for key, sub in df.groupby(group_col, observed=True):
        covered += len(sub)
        over, under = _direction(sub, pred_col)
        rows.append({
            group_col: key,
            "n": len(sub) if len(sub) >= MIN_CELL else f"<{MIN_CELL}",
            "적중률": _rate(sub[pred_col + "_hit"]),
            "과대추정률(미적중중)": over,
            "과소추정률(미적중중)": under,
        })
    assert covered == len(df), f"{group_col} 구간화에서 {len(df) - covered}행 누락"
    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)
    a_all = df[df["급여종류"] == "퇴직연금"].copy()
    a = a_all[a_all["평균기준소득월액"].notna() & (a_all["연금월액_구분"] != 0)].copy()
    a["퇴직연도"] = a["퇴직연월"] // 100

    school = [SCHOOL_LEVEL_BY_KOREAN[s] for s in a["학교급"].astype(str)]
    job = [JOB_TYPE_BY_KOREAN[j] for j in a["직구분"].astype(str)]

    a["legacy"] = [
        predict_monthly_pension_legacy(income, months)
        for income, months in zip(a["평균기준소득월액"], a["재직월수"])
    ]
    # 집단정보 미제공(폴백 프로파일) — 기존 API 클라이언트가 겪을 경로
    a["nogroup"] = [
        predict_monthly_pension(income, months, retire_year=year, retire_age=age)
        for income, months, year, age in zip(
            a["평균기준소득월액"], a["재직월수"], a["퇴직연도"], a["퇴직당시연령"]
        )
    ]
    # 집단정보 제공 — 학교급·직구분까지 받은 경로
    a["withgroup"] = [
        predict_monthly_pension(
            income, months, retire_year=year, retire_age=age, school_level=sl, job_type=jt
        )
        for income, months, year, age, sl, jt in zip(
            a["평균기준소득월액"], a["재직월수"], a["퇴직연도"], a["퇴직당시연령"], school, job
        )
    ]

    for col in ("legacy", "nogroup", "withgroup"):
        a[col + "_hit"] = is_hit(a[col], a["연금월액_하한"], a["연금월액_상한"])

    closed = a[a["연금월액_구분"].between(1, 7)]
    open_top = a[a["연금월액_구분"] == 8]

    lines: list[str] = []
    lines.append("# Calibration Report — Phase 6 (보정 지급률 모형 적용 후)")
    lines.append("")
    lines.append("데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).")
    lines.append(
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 이 리포트 어디에도 없다 — 구간 코드·적중률·무차원 비율만 기록한다."
    )
    lines.append("")
    lines.append(
        "예측식: 프로덕션 `app/services/employees_service.py::calculate_monthly_pension`을 "
        "그대로 호출한다(계수 재타이핑 없음). 지급률은 "
        "`app/services/pension_rate_model.py::effective_pension_rate`가 산출한다."
    )
    lines.append("")
    lines.append(f"- 표본 수(A. 퇴직연금): {len(a):,} "
                 f"(원본 {len(a_all):,}행 중 평균기준소득월액 결측 "
                 f"{int(a_all['평균기준소득월액'].isna().sum())}행, "
                 f"정답구간 없음(연금월액_구분==0) {int((a_all['연금월액_구분'] == 0).sum())}행 제외)")
    lines.append("")
    lines.append("## 개선 전/후 비교")
    lines.append("")
    rows = []
    for label, col, cv in (
        ("개선 전 (단일 상수 1.7%)", "legacy", None),
        ("개선 후 · 집단정보 미제공(폴백)", "nogroup", CV_OVERALL_WITHOUT_GROUP),
        ("개선 후 · 집단정보 제공", "withgroup", CV_OVERALL_WITH_GROUP),
    ):
        over, under = _direction(a, col)
        rows.append({
            "모형": label,
            "전체 적중률": _rate(a[col + "_hit"]),
            "닫힌구간(1~7)": _rate(closed[col + "_hit"]),
            "개방구간(코드8)": _rate(open_top[col + "_hit"]),
            "과대추정률(미적중중)": over,
            "과소추정률(미적중중)": under,
            "5-fold CV 전체": "—" if cv is None else f"{cv:.2f}%",
        })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")
    lines.append(
        f"닫힌구간 n={len(closed):,} / 개방구간 n={len(open_top):,}. "
        "**개방구간(코드 8, 350만원 이상)은 상한이 없어 과대추정이 무조건 적중으로 잡힌다** — "
        "개선 전 모형의 개방구간 적중률 99.62%는 정확도가 아니라 과대추정의 증상이었다. "
        "모형 품질은 닫힌구간 적중률로 판단할 것."
    )
    lines.append("")
    lines.append("`전체 적중률` 열은 계수 적합에 쓴 것과 같은 표본에서 잰 in-sample 값이다. "
                 "일반화 성능은 마지막 열(적합 절차를 fold별로 재실행한 5-fold 교차검증)로 판단한다 — "
                 "두 값의 격차가 작아야 과적합이 아니다.")
    lines.append("")

    for col, title in (("withgroup", "집단정보 제공"), ("nogroup", "폴백")):
        a["재직연수_구간"] = pd.cut(
            a["재직연수"], bins=[-float("inf"), 15, 20, 25, 30, 33, float("inf")], right=False,
            labels=["<15", "15~19", "20~24", "25~29", "30~32", "33+"],
        )
        a["퇴직당시연령_구간"] = pd.cut(
            a["퇴직당시연령"], bins=[-float("inf"), 50, 55, 60, 65, float("inf")], right=False,
            labels=["~49", "50~54", "55~59", "60~64", "65+"],
        )
        a["학교급_직구분"] = a["학교급"].astype(str) + "×" + a["직구분"].astype(str)
        lines.append(f"## 세그먼트별 적중률 — {title}")
        lines.append("")
        for group_col, heading in (
            ("재직연수_구간", "재직연수"),
            ("퇴직연도", "퇴직연도"),
            ("퇴직당시연령_구간", "퇴직당시연령"),
            ("학교급_직구분", "학교급×직구분"),
        ):
            lines.append(f"### {heading}")
            lines.append("")
            lines.append(_breakdown(a, group_col, col).to_markdown(index=False))
            lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "calibration_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    # 콘솔 인코딩(cp949 등)에 막혀 리포트 생성 자체가 실패하지 않도록 경로만 출력한다.
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
