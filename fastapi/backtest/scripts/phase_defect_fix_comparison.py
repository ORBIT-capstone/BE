"""engine_defects.md #1(재직기간 상한 일괄 36년)·#2(조기수령 감액 소수 미대응) 수정 전/후
비교 (Step 4). #2는 A(퇴직연금) baseline 채점 경로(employees_service.py)와 무관하므로
(early_years는 retirement_service.py::simulate_scenarios 전용) 이 스크립트가 실측하는
것은 사실상 #1(및 Step 1c: LUMP_SUM/SPLIT 재직연수 상한) 반영 여부다. #1c는 A(퇴직연금)
baseline/Tier1 채점 경로와 무관한 별도 엔드포인트(scenarios)라 여기 수치에 영향이 없다
— 아래에서 실측으로 확인한다(가정하지 않는다).

표본·필터·판정 기준은 기존 phase3_baseline.py/phase4_tier1.py와 동일하게 유지한다
(재사용 모듈: engine_baseline.py, tranche.py, interval_utils.py). "before"는
service_months_as_of_2016을 넘기지 않아 DEFAULT_MAX(36년 고정, 이전 baseline과 동일)로
판정되고, "after"는 추정임용연월로부터 역산한 2016.1.1 시점 인정 재직월수를 넘겨
사학연금법 부칙 제11조 경과조치 표(33/34/35/36년 차등)를 적용한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKTEST_DIR / "scripts"))

from engine_baseline import (  # noqa: E402
    predict_monthly_pension,
    service_months_as_of_2016_from_appointment,
)
from interval_utils import is_hit  # noqa: E402
from tranche import decompose_tranche_months, predict_tier1  # noqa: E402

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"
MIN_CELL = 5

TENURE_BINS = [-float("inf"), 10, 15, 20, 25, 30, 33, 34.0001, float("inf")]
TENURE_LABELS = ["<10", "10~14", "15~19", "20~24", "25~29", "30~32", "33~34", "34+"]


def _rate_str(hit: pd.Series) -> str:
    n = len(hit)
    if n < MIN_CELL:
        return "n<5 (마스킹)"
    return f"{hit.mean() * 100:.2f}%"


def _direction_rates(predicted: pd.Series, lower: pd.Series, upper: pd.Series, hit: pd.Series) -> tuple[str, str]:
    miss = ~hit
    n_miss = int(miss.sum())
    if n_miss < MIN_CELL:
        return "n<5 (마스킹)", "n<5 (마스킹)"
    over = int((predicted[miss] >= upper[miss]).sum())
    under = int((predicted[miss] < lower[miss]).sum())
    assert over + under == n_miss
    return f"{over / n_miss * 100:.2f}%", f"{under / n_miss * 100:.2f}%"


def _summary_row(label: str, df: pd.DataFrame, pred_col: str) -> dict:
    hit = is_hit(df[pred_col], df["연금월액_하한"], df["연금월액_상한"])
    closed = df["연금월액_구분"].between(1, 7)
    open8 = df["연금월액_구분"] == 8
    over, under = _direction_rates(df[pred_col], df["연금월액_하한"], df["연금월액_상한"], hit)
    return {
        "구분": label,
        "전체 적중률": _rate_str(hit),
        "닫힌구간 적중률": _rate_str(hit[closed]),
        "개방구간(코드8) 적중률": _rate_str(hit[open8]),
        "과대추정률(미적중중)": over,
        "과소추정률(미적중중)": under,
    }


def _tenure_breakdown(df: pd.DataFrame, pred_col: str, label: str) -> pd.DataFrame:
    tenure_bin = pd.cut(df["재직연수"], bins=TENURE_BINS, right=False, labels=TENURE_LABELS)
    rows = []
    for bucket, sub in df.groupby(tenure_bin, observed=True):
        hit = is_hit(sub[pred_col], sub["연금월액_하한"], sub["연금월액_상한"])
        rows.append({"재직연수_구간": bucket, "구분": label, "n": len(sub), "적중률": _rate_str(hit)})
    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)

    # ============ 표 A: 전체 A 표본 (baseline_report.md 범위, n=40,719) ============
    a_all = df[(df["급여종류"] == "퇴직연금") & (df["평균기준소득월액"].notna())].copy()
    n_missing_income = int(a_all["평균기준소득월액"].isna().sum())  # 항상 0 (이미 notna 필터)
    a = a_all[a_all["연금월액_구분"] != 0].copy()

    a["sm2016"] = service_months_as_of_2016_from_appointment(a["추정임용연월"])
    a["pred_before"] = [predict_monthly_pension(i, m) for i, m in zip(a["평균기준소득월액"], a["재직월수"])]
    a["pred_after"] = [
        predict_monthly_pension(i, m, s) for i, m, s in zip(a["평균기준소득월액"], a["재직월수"], a["sm2016"])
    ]
    changed_mask = a["pred_before"] != a["pred_after"]
    n_changed = int(changed_mask.sum())
    changed_detail = a.loc[
        changed_mask,
        ["재직월수", "재직연수", "재직월수_상한도달여부", "sm2016"],
    ].copy()
    changed_detail["법정상한값(396/408/420/432) 자체와 일치"] = changed_detail["재직월수"].isin(
        [396, 408, 420, 432]
    )

    summary_a = pd.DataFrame([_summary_row("BEFORE(36년 고정)", a, "pred_before"), _summary_row("AFTER(부칙 제11조 차등)", a, "pred_after")])
    tenure_before = _tenure_breakdown(a, "pred_before", "BEFORE")
    tenure_after = _tenure_breakdown(a, "pred_after", "AFTER")
    tenure_merged = tenure_before.merge(
        tenure_after, on="재직연수_구간", suffixes=("_before", "_after")
    )[["재직연수_구간", "n_before", "적중률_before", "적중률_after"]].rename(
        columns={"n_before": "n"}
    )

    # ============ 표 B: tranche 분해 대상 표본 (tier1_evaluation.md 범위) ============
    n_capped = int(a_all["재직월수_상한도달여부"].sum())
    sample = a_all[~a_all["재직월수_상한도달여부"]].copy()
    sample = sample[sample["연금월액_구분"] != 0].copy()

    sample["sm2016"] = service_months_as_of_2016_from_appointment(sample["추정임용연월"])
    sample["baseline_before"] = [
        predict_monthly_pension(i, m) for i, m in zip(sample["평균기준소득월액"], sample["재직월수"])
    ]
    sample["baseline_after"] = [
        predict_monthly_pension(i, m, s)
        for i, m, s in zip(sample["평균기준소득월액"], sample["재직월수"], sample["sm2016"])
    ]
    n_changed_sample = int((sample["baseline_before"] != sample["baseline_after"]).sum())

    tranche_months = decompose_tranche_months(sample["추정임용연월"], sample["재직월수"], offset_months=0)
    sample["tier1_pred"] = predict_tier1(sample["평균기준소득월액"], tranche_months)

    summary_b = pd.DataFrame(
        [
            _summary_row("baseline BEFORE(36년 고정)", sample, "baseline_before"),
            _summary_row("baseline AFTER(부칙 제11조 차등)", sample, "baseline_after"),
            _summary_row("Tier1 (Step1/2/1c와 무관, 불변 확인용)", sample, "tier1_pred"),
        ]
    )

    # ============ 리포트 작성 ============
    lines: list[str] = []
    lines.append("# Engine Defect Fix — Before/After 비교 (Step 4)")
    lines.append("")
    lines.append("데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).")
    lines.append(
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 이 리포트 어디에도 없다."
    )
    lines.append("")
    lines.append(
        "대상: `engine_defects.md` #1(재직기간 상한 일괄 36년). #2(조기수령 감액)와 Step 1c "
        "(LUMP_SUM/SPLIT 상한)는 `retirement_service.py`(scenarios 엔드포인트) 전용이라 "
        "A(퇴직연금) baseline/Tier1 채점 경로(employees_service.py 기반)와 무관하다 — "
        "아래 수치가 실제로 이 두 변경 전후 동일한지 실측으로 확인한다(가정하지 않는다)."
    )
    lines.append("")
    lines.append("## 결론 (먼저 읽을 것)")
    lines.append("")
    lines.append(
        "- **이 결함은 본 데이터셋으로 검증 불가능하다.** 공단이 제공한 `재직월수`는 이미 "
        "법정 상한이 적용된 **인정 재직기간**이다 — A 표본 전체에서 396개월을 초과하는 "
        "행이 단 3건(398·408·408개월)뿐이고 그중 2건은 그 자체로 법정 상한값(408=34년)과 "
        "일치한다는 것이 그 증거다. 즉 이 표본 안에서는 엔진의 재직기간 상한 로직이 "
        "발동할 여지가 구조적으로 거의 없다 — 표본 크기를 늘려도 이 결함의 영향을 이 "
        "데이터로는 측정할 수 없다."
    )
    lines.append(
        "- **반면 서비스 경로(재직자 API)에서는 결함이 실재한다.** `/api/employees/simulate`는 "
        "사용자가 `current_years`(상한 미적용, 캘린더 재직연수)를 직접 입력받으므로, 실제 "
        "36년을 초과해 재직한 사용자가 입력하면 수정 전 코드는 상한을 잘못 적용했다. 이 "
        "결함의 수정 효과는 (이 데이터로 측정할 수 없으므로) 백테스트가 아니라 "
        "`tests/test_employees_service.py`의 경계값 단위테스트(179/180/181,203/204/205,"
        "251/252/253개월)로 확인했다."
    )
    lines.append(
        "- **baseline의 과대추정(98%)은 이 결함으로 설명되지 않는다.** 아래 표 A·B가 보여주듯 "
        "수정 전/후 적중률은 사실상 그대로다. 과대추정의 원인은 여전히 보정률·소득재분배·"
        "현가환산 등 미구현 요소 쪽으로 봐야 한다는 기존 결론(`tier1_evaluation.md`)이 유지된다."
    )
    lines.append("")
    lines.append("## 표 A — 전체 A 표본 (n={:,}, baseline_report.md와 동일 범위)".format(len(a)))
    lines.append("")
    lines.append(summary_a.to_markdown(index=False))
    lines.append("")
    lines.append(f"예측값이 실제로 달라진 행 수: {n_changed:,} / {len(a):,}")
    lines.append("")
    lines.append("### 각주 — 예측값이 바뀐 3행의 특성 (원본 금액 미포함)")
    lines.append("")
    lines.append(changed_detail.reset_index(drop=True).to_markdown(index=False))
    lines.append("")
    lines.append(
        "3행 전부 396개월(33년) 초과 행이며, A 표본 전체에서 396개월 초과 행은 이 3건이 "
        "전부다(398개월 1건, 408개월 2건 — 위 표의 유일한 초과 사례군과 정확히 일치)."
    )
    lines.append(
        "- 408개월(정확히 34.0년) 2건은 `재직월수_상한도달여부=True` — 이 값 자체가 법정 "
        "상한값(34년) 중 하나와 일치한다. 원본 시스템이 이 사람의 실제 2016.1.1 시점 "
        "재직기간 구간(아마 17년 이상~21년 미만)에 따라 이미 34년으로 절단했을 가능성이 "
        "높아 보이지만, 실제 2016.1.1 시점 재직기간을 공식적으로 확인할 방법이 없어 "
        "**미상**이다. 이 스크립트가 역산한 sm2016(335·359개월, 21년 이상 구간)과 34년 "
        "절단이 서로 다른 구간을 가리키는 것은, sm2016 자체가 추정임용연월(근사치)에서 "
        "역산한 값이기 때문일 수 있다 — 이 역시 **미상**이며 데이터 품질 이슈로 단정하지 "
        "않는다(scope_limitations.md §2-1의 근사치 한계 참조)."
    )
    lines.append(
        "- 398개월(33.17년) 1건은 법정 상한값이 아니다 — 33년을 소폭 초과하는 값으로, "
        "정년 초과 재직 등 실제 사유로 33년을 넘겼을 가능성과 인정 재직기간 집계상의 "
        "특이 케이스일 가능성을 구분할 근거가 없다 — **미상**으로 남긴다."
    )
    lines.append("")
    lines.append("### 재직연수 구간별 적중률 (전체 A 표본)")
    lines.append("")
    lines.append(tenure_merged.to_markdown(index=False))
    lines.append("")
    lines.append("## 표 B — tranche 분해 대상 표본 (n={:,}, tier1_evaluation.md와 동일 범위)".format(len(sample)))
    lines.append("")
    lines.append(summary_b.to_markdown(index=False))
    lines.append("")
    lines.append(f"baseline 예측값이 실제로 달라진 행 수: {n_changed_sample:,} / {len(sample):,}")
    tier1_unaffected = (
        summary_b.loc[summary_b["구분"].str.startswith("Tier1"), "전체 적중률"].iloc[0]
    )
    lines.append(
        f"Tier1 전체 적중률: {tier1_unaffected} — Step 1/2/1c는 tranche.py·employees_service.py의 "
        "Tier1 계산 경로를 전혀 거치지 않으므로 이 값은 수정 전 tier1_evaluation.md에 이미 "
        "기록된 값(35.00%)과 같아야 한다. 위 표 값과 대조해 실제로 같은지 확인할 것."
    )
    lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "defect_fix_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print()
    print(f"[assert-check] n_missing_income={n_missing_income} (should be 0)")


if __name__ == "__main__":
    main()
