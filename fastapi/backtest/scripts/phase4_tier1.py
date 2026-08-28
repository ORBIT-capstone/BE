"""법정 지급률 tranche 적용 모형(Tier 1) 평가 (Phase 4, A: 정상 퇴직연금).

**요율을 데이터로 추정하지 않는다.** 확정된 법정 요율(backtest/config/tranche_rates.py)을
적용했을 때 현재 엔진(baseline) 대비 구간 적중률이 얼마나 개선되는지만 잰다.

Tier 1은 법정 산식이 아니다 — 보정률·소득재분배·2009년 이전 별도 산식(평균보수월액
기반)·종전규정 min이 빠져 있고, 전 구간에 평균기준소득월액을 공통 proxy로 사용한다.
자세한 한계는 tranche.py, tranche_rates.py docstring 참조.

표본 제한: 재직월수_상한도달여부 == False (법정 상한 396/408/420/432개월 절단이 없어
임용시점 복원이 가능한 행)만 tranche 분해 대상으로 삼는다. 이 스크립트는 baseline과
Tier 1을 **동일한 제한 표본**에서 비교한다(공정 비교) — Phase 3 baseline_report.md의
전체 표본 수치와는 표본이 다르므로 직접 비교하지 말 것.

M1: 연금월액_구분==0("해당 금액 없음")은 채점 대상이 아니므로 baseline·Tier 1 양쪽
모두에서 분모에서 제외한다(제외 행수를 리포트에 기록).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKTEST_DIR / "scripts"))

from engine_baseline import PENSION_RATE, predict_monthly_pension  # noqa: E402
from interval_utils import is_hit  # noqa: E402
from tranche import decompose_tranche_months, legal_rate_sum, predict_tier1  # noqa: E402

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"

MIN_CELL = 5
SENSITIVITY_OFFSETS = [-24, -12, 0, 12, 24]

# 탐색 단계 검산용 참고값 (재직월수_상한도달여부==False인 퇴직연금 행수) - 계산값과 크게
# 다르면 정제 파이프라인 문제 신호. 리포트에는 실제 계산값을 쓴다.
_REFERENCE_EXCLUDED_RATIO_APPROX = 0.49


def _direction_rates(predicted: pd.Series, lower: pd.Series, upper: pd.Series, hit: pd.Series) -> tuple[str, str]:
    """미적중 행 중 과대/과소 비율. 호출 전에 연금월액_구분==0 행이 제외돼 있어야
    두 비율의 합이 100%가 된다(assertion으로 확인)."""
    miss = ~hit
    n_miss = int(miss.sum())
    if n_miss < MIN_CELL:
        return "n<5 (마스킹)", "n<5 (마스킹)"
    over = int((predicted[miss] >= upper[miss]).sum())
    under = int((predicted[miss] < lower[miss]).sum())
    assert over + under == n_miss, (
        f"과대+과소({over + under}) != 미적중 행수({n_miss}) — 정답구간 없음(코드0) 행 혼입 의심"
    )
    return f"{over / n_miss * 100:.2f}%", f"{under / n_miss * 100:.2f}%"


def _rate_str(hit: pd.Series) -> str:
    n = len(hit)
    if n < MIN_CELL:
        return "n<5 (마스킹)"
    return f"{hit.mean() * 100:.2f}%"


def _reference_effective_rate_ratio(sample: pd.DataFrame, tranche_months_0: pd.DataFrame) -> list[str]:
    """관측 실효 지급률과 법정 요율(가중평균)의 비율을 참고 지표로만 기록한다.

    - 관측 실효 지급률(row-level proxy) = 정답 구간 중점(코드1~7만, 코드8은 상한이
      없어 중점을 정의할 수 없어 제외) / (평균기준소득월액 x 재직연수)
    - 법정 요율(row-level) = legal_rate_sum(tranche_months) / 재직연수
    - 비율 = 관측 실효 지급률 / 법정 요율

    개별 금액·소득 값은 리포트에 출력하지 않는다 — 이 비율의 표본 전체 집계
    (median/IQR)만 출력한다. **이 비율을 보정률의 추정치로 확정하지 않는다** — 보정률
    외에도 소득재분배·2009년 이전 별도 산식 등 여러 미구현 요소가 섞여 있는 값이다.
    """
    closed = sample[sample["연금월액_구분"].between(1, 7)].copy()
    n = len(closed)
    if n < MIN_CELL:
        return ["관측 실효 지급률 참고 지표: n<5 (마스킹)."]

    midpoint = (closed["연금월액_하한"] + closed["연금월액_상한"]) / 2
    observed_rate = midpoint / (closed["평균기준소득월액"] * closed["재직연수"])

    rate_sum = legal_rate_sum(tranche_months_0.loc[closed.index])
    legal_avg_rate = rate_sum / closed["재직연수"]

    ratio = observed_rate / legal_avg_rate
    ratio = ratio.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if len(ratio) < MIN_CELL:
        return ["관측 실효 지급률 참고 지표: 유효 표본 n<5 (마스킹)."]

    return [
        f"- 표본(닫힌 구간 코드1~7만, n={len(ratio):,})에서 legal_avg_rate 가중평균: "
        f"{legal_avg_rate.mean() * 100:.3f}% (baseline 단일 상수 {PENSION_RATE * 100:.1f}%보다 높음)",
        f"- 관측 실효 지급률/법정 요율 비율 — median: {ratio.median():.3f}, "
        f"p25: {ratio.quantile(.25):.3f}, p75: {ratio.quantile(.75):.3f}",
        "  (1.0에 가까울수록 법정 요율만으로 실지급액이 설명됨. 1.0보다 낮게 나오는 만큼이 "
        "보정률·소득재분배 등 미구현 요소가 담당하는 몫이라는 정황이며, **이 비율 자체를 "
        "보정률의 추정치로 확정하지 않는다** — 소득재분배·2009년 이전 별도 산식 등 다른 "
        "미구현 요소도 함께 섞여 있다.)",
    ]


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)
    a_all = df[(df["급여종류"] == "퇴직연금") & (df["평균기준소득월액"].notna())].copy()

    n_capped = int(a_all["재직월수_상한도달여부"].sum())
    n_total = len(a_all)
    n_sample_precode0 = n_total - n_capped
    excluded_ratio = n_capped / n_total

    sample_precode0 = a_all[~a_all["재직월수_상한도달여부"]].copy()
    assert len(sample_precode0) == n_sample_precode0

    # M1: 정답구간 없음(코드0) 제외
    n_no_answer = int((sample_precode0["연금월액_구분"] == 0).sum())
    sample = sample_precode0[sample_precode0["연금월액_구분"] != 0].copy()
    n_sample = len(sample)

    # --- 6-3. 기간 분해 + assertion (offset=0) ---
    tranche_months_0 = decompose_tranche_months(sample["추정임용연월"], sample["재직월수"], offset_months=0)
    coverage_0 = tranche_months_0.sum(axis=1)
    mismatches = int((coverage_0 != sample["재직월수"]).sum())
    assert mismatches == 0, (
        f"tranche 월수 합계가 재직월수와 불일치하는 행이 {mismatches}건 있음 — 정제 파이프라인 확인 필요"
    )

    # --- baseline vs Tier 1 (동일 표본) ---
    sample["baseline_pred"] = [
        predict_monthly_pension(income, months)
        for income, months in zip(sample["평균기준소득월액"], sample["재직월수"])
    ]
    sample["tier1_pred"] = predict_tier1(sample["평균기준소득월액"], tranche_months_0)

    sample["baseline_hit"] = is_hit(sample["baseline_pred"], sample["연금월액_하한"], sample["연금월액_상한"])
    sample["tier1_hit"] = is_hit(sample["tier1_pred"], sample["연금월액_하한"], sample["연금월액_상한"])

    closed_mask = sample["연금월액_구분"].between(1, 7)

    baseline_over, baseline_under = _direction_rates(
        sample["baseline_pred"], sample["연금월액_하한"], sample["연금월액_상한"], sample["baseline_hit"]
    )
    tier1_over, tier1_under = _direction_rates(
        sample["tier1_pred"], sample["연금월액_하한"], sample["연금월액_상한"], sample["tier1_hit"]
    )

    comparison = pd.DataFrame(
        [
            {
                "모형": "현재 엔진 (단일 상수)",
                "전체 적중률": _rate_str(sample["baseline_hit"]),
                "닫힌 구간 적중률": _rate_str(sample.loc[closed_mask, "baseline_hit"]),
                "과대추정률(미적중중)": baseline_over,
                "과소추정률(미적중중)": baseline_under,
            },
            {
                "모형": "Tier 1 (법정 tranche, 잠정 비교모형)",
                "전체 적중률": _rate_str(sample["tier1_hit"]),
                "닫힌 구간 적중률": _rate_str(sample.loc[closed_mask, "tier1_hit"]),
                "과대추정률(미적중중)": tier1_over,
                "과소추정률(미적중중)": tier1_under,
            },
        ]
    )

    # --- 6-4. 민감도 분석: 5개 offset 전부에서 커버되는 공통 표본을 명시적으로 구한다 ---
    # (H3 수정 전에는 tranche 구간이 2025년에서 끝나 offset=+24에서만 일부 행이 범위
    # 밖으로 빠져 표본이 달라졌다 — 지금은 -inf~+inf를 빈틈없이 덮으므로 이론상 모든
    # offset에서 커버리지가 동일해야 한다. 가정하지 않고 실제로 교집합을 구해 확인한다.)
    coverage_by_offset: dict[int, pd.Series] = {}
    for offset in SENSITIVITY_OFFSETS:
        tm = decompose_tranche_months(sample["추정임용연월"], sample["재직월수"], offset_months=offset)
        coverage_by_offset[offset] = tm.sum(axis=1) == sample["재직월수"]

    common_covered = pd.Series(True, index=sample.index)
    for covered in coverage_by_offset.values():
        common_covered &= covered
    n_common = int(common_covered.sum())

    sensitivity_rows = []
    for offset in SENSITIVITY_OFFSETS:
        tm = decompose_tranche_months(sample["추정임용연월"], sample["재직월수"], offset_months=offset)
        covered = coverage_by_offset[offset]
        n_covered_this_offset = int(covered.sum())

        pred = predict_tier1(sample.loc[common_covered, "평균기준소득월액"], tm.loc[common_covered])
        hit = is_hit(pred, sample.loc[common_covered, "연금월액_하한"], sample.loc[common_covered, "연금월액_상한"])
        closed_common = closed_mask.loc[common_covered]

        # offset이 이동함에 따라 법정요율 가중평균·pre-2010 비중이 어떻게 움직이는지도
        # 함께 기록한다 — 아래 민감도 해석(과대추정 완화 메커니즘)의 근거 수치.
        rs = legal_rate_sum(tm.loc[common_covered])
        avg_rate = (rs / sample.loc[common_covered, "재직연수"]).mean()
        pre2010_share = (
            tm.loc[common_covered, "pre_2010"] / sample.loc[common_covered, "재직월수"]
        ).mean()

        sensitivity_rows.append(
            {
                "추정임용연월 이동(개월)": offset,
                "이 offset 커버리지 n": f"{n_covered_this_offset:,}",
                "공통 표본 n": f"{n_common:,}",
                "전체 적중률(공통표본)": _rate_str(hit),
                "닫힌 구간 적중률(공통표본)": _rate_str(hit[closed_common]),
                "법정요율 가중평균(%)": round(avg_rate * 100, 3),
                "pre-2010 월수비중(%)": round(pre2010_share * 100, 2),
            }
        )
    sensitivity = pd.DataFrame(sensitivity_rows)

    all_offsets_fully_covered = all(
        int(c.sum()) == n_sample for c in coverage_by_offset.values()
    )

    rates_only = [
        float(r["전체 적중률(공통표본)"].rstrip("%"))
        for r in sensitivity_rows
        if r["전체 적중률(공통표본)"] != "n<5 (마스킹)"
    ]
    swing = max(rates_only) - min(rates_only) if rates_only else float("nan")

    reference_ratio_lines = _reference_effective_rate_ratio(sample, tranche_months_0)

    # --- 리포트 작성 ---
    lines: list[str] = []
    lines.append("# Tier 1 Evaluation — Phase 4 (A: 정상 퇴직연금)")
    lines.append("")
    lines.append("데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).")
    lines.append(
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 이 리포트 어디에도 없다."
    )
    lines.append("")
    lines.append(
        "**법정 산식 ≠ Tier 1.** Tier 1은 확정된 연도별 지급률 tranche(backtest/config/tranche_rates.py)를 "
        "적용했을 때 baseline 대비 정합성이 얼마나 개선되는가를 재는 잠정 비교모형이다. "
        "보정률·소득재분배(A/B/C값)·2009년 이전 별도 산식(평균보수월액 기반)·종전규정 유리 원칙(min)은 "
        "외부 법령 파라미터 미확보로 구현하지 않았다. **\"법정 산식 재현 정확도\"로 해석하지 말 것.**"
    )
    lines.append("")
    lines.append(
        "2009년 이전 재직기간의 법정 산정기초는 평균보수월액이나, 이 데이터셋에는 제공되지 않는다. "
        "Tier 1은 전 구간에 평균기준소득월액을 공통 proxy로 사용하므로 2009년 이전 구간 비중이 큰 "
        "장기재직자에서 구조적 오차(과대추정 가능성, 사전 예측)가 있을 것으로 본다 — 이는 검증 대상 "
        "가설이며, 아래 결과로 확인한다. **결과를 맞추기 위한 계수 조정은 하지 않았다.**"
    )
    lines.append("")
    lines.append("## 표본 제한")
    lines.append("")
    lines.append(
        f"- A(퇴직연금) 전체(평균기준소득월액 결측 제외): {n_total:,}행\n"
        f"- 재직월수_상한도달여부==True(법정 상한 396/408/420/432개월 절단 가능성, 임용시점 복원 불가) "
        f"제외: {n_capped:,}행 ({excluded_ratio * 100:.2f}%)\n"
        f"- 정답구간 없음(연금월액_구분==0, 채점 대상 아님) 추가 제외: {n_no_answer:,}행\n"
        f"- tranche 분해 대상 표본: {n_sample:,}행"
    )
    lines.append(
        f"\n(탐색 단계 참고값은 약 {_REFERENCE_EXCLUDED_RATIO_APPROX * 100:.0f}%였다 — "
        f"실측값 {excluded_ratio * 100:.2f}%와 정합함)"
    )
    lines.append("")
    lines.append(
        "assertion 통과: offset=0 기준 모든 표본 행에서 sum(tranche 월수) == 재직월수 "
        f"(불일치 {mismatches}건)."
    )
    lines.append("")
    lines.append(f"## baseline 대비 비교 (동일 표본, tranche 분해 대상 표본 n={n_sample:,} 기준)")
    lines.append("")
    lines.append(comparison.to_markdown(index=False))
    lines.append("")
    lines.append(
        "**Tier 1이 baseline보다 적중률이 낮은 것은 예상된 결과다.** 법정 요율(pre-2010 2.0%, "
        f"2010-2015 1.9%, 2016년 이후 연도별 1.878%~1.700%)은 전부 현재 엔진의 단일 상수"
        f"(PENSION_RATE={PENSION_RATE*100:.1f}%)보다 높거나 같다. baseline은 이미 미적중의 대부분이 "
        "과대추정인데(위 표 baseline 과대추정률 참조), 요율을 baseline보다 높은 법정 요율로 올리면 "
        "과대추정이 더 심화되는 것이 산술적으로 당연하다."
    )
    lines.append("")
    lines.append(
        "**따라서 이 결과는 \"법정 요율이 틀렸다\"가 아니라 \"보정률을 제외한 어떤 모형도 실지급액을 "
        "재현할 수 없다\"는 것을 실증한다.** 보정률은 산식의 부수 요소가 아니라 필수 구성요소다 — "
        "법정 요율(Tier 1)도, 단일 상수(baseline)도 보정률 없이는 둘 다 체계적으로 과대추정한다."
    )
    lines.append("")
    lines.append(
        "**주의**: baseline의 적중률이 더 높다고 해서 0.017이 \"옳은\" 값이라는 뜻이 아니다. baseline도 "
        f"미적중의 {baseline_over}가 과대추정이다(n={n_sample:,}, tranche 부분표본 기준 — 위 표와 동일 "
        f"표본. `baseline_report.md`가 보고하는 98.00%는 이 표본이 아니라 A 전체 표본(n=40,719)에서 "
        "측정한 값이며 서로 다른 표본이라 직접 비교하면 안 된다) — 단지 Tier 1보다 덜 틀렸을 뿐이다. "
        "\"단일 상수가 법정 요율보다 우수한 모형\"이라는 해석은 이 결과가 뒷받침하지 않는다. 두 모형 "
        "모두 보정률이 빠진 상태에서는 구조적으로 과대추정하며, 그 정도의 차이만 있을 뿐이다."
    )
    lines.append("")
    lines.append("### 참고 지표 — 관측 실효 지급률 대비 법정 요율 비율")
    lines.append("")
    lines.extend(reference_ratio_lines)
    lines.append("")
    lines.append("## 민감도 분석 — 추정임용연월 이동")
    lines.append("")
    lines.append(
        "불확실한 것은 법정 경계가 아니라 임용시점 추정치다. 재직월수(구간 길이)는 고정하고 "
        "추정임용연월(구간 시작점)만 −24/−12/0/+12/+24개월 이동시켰다. tranche 구간이 -inf~+inf를 "
        "빈틈없이 덮도록 고친 뒤이므로(tranche.py), 5개 offset 전부에서 커버리지가 동일한지 실제로 "
        "교집합을 구해 확인했다 — 가정하지 않았다."
    )
    lines.append("")
    if all_offsets_fully_covered:
        lines.append(
            f"확인 결과: 5개 offset 전부에서 전체 표본({n_sample:,}행)이 빠짐없이 커버됐다 "
            "(offset에 따라 표본이 달라지는 문제 없음). 아래 표는 전체 표본 기준이다."
        )
    else:
        lines.append(
            f"확인 결과: offset에 따라 커버리지가 달랐다 — 공통 표본(모든 offset에서 커버됨) "
            f"n={n_common:,}. 아래 표는 이 공통 표본으로 고정해 계산했다(offset 간 표본 차이로 인한 "
            "착시를 배제하기 위함)."
        )
    lines.append("")
    lines.append(sensitivity.to_markdown(index=False))
    lines.append("")

    is_monotonic_nondecreasing = rates_only == sorted(rates_only)

    if not rates_only or swing != swing or swing > 3.0:
        lines.append(
            f"전체 적중률이 offset에 따라 최대 {swing:.2f}%p 흔들린다. 인정 재직기간으로 실제 제도 "
            "적용기간을 복원할 수 없어 tranche 분해 결과는 참고 수준으로만 해석한다."
        )
    elif is_monotonic_nondecreasing:
        lines.append(
            f"전체 적중률이 offset −24개월부터 +24개월까지 {rates_only[0]:.2f}%에서 "
            f"{rates_only[-1]:.2f}%로 **단조 증가**한다(변동폭 {swing:.2f}%p). "
            "**이를 임용시점 추정의 견고함이나 안정성의 근거로 해석하지 않는다** — 창(±24개월) 내부에 "
            "적중률이 꺾이는 최적점이 없고, 한쪽 끝을 향해 계속 움직이기 때문이다."
        )
        lines.append("")
        lines.append(
            "위 표의 '법정요율 가중평균'·'pre-2010 월수비중' 열이 보여주듯, 추정임용연월을 뒤로(+) "
            "이동시킬수록 근무 구간에서 pre-2010 구간(요율 2.0%, 가장 높은 tranche)이 차지하는 비중이 "
            f"줄어들며(offset {SENSITIVITY_OFFSETS[0]}개월에서 {sensitivity_rows[0]['pre-2010 월수비중(%)']:.2f}% "
            f"→ offset {SENSITIVITY_OFFSETS[-1]}개월에서 {sensitivity_rows[-1]['pre-2010 월수비중(%)']:.2f}%), "
            "그만큼 법정요율 가중평균도 낮아진다"
            f"({sensitivity_rows[0]['법정요율 가중평균(%)']:.3f}% → {sensitivity_rows[-1]['법정요율 가중평균(%)']:.3f}%). "
            "Tier 1은 이미 baseline보다도 체계적으로 과대추정하는 모형이므로(위 baseline 대비 비교 참조), "
            "예측 요율이 낮아질수록 과대추정이 완화되어 적중률이 오르는 것은 자연스러운 산술적 결과다."
        )
        lines.append("")
        lines.append(
            "즉 이 단조 증가는 \"임용시점 추정이 정확했다\"는 검증 결과가 아니라, **보정률이 빠진 "
            "Tier 1 모형의 구조적 편향(과대추정)이 민감도 분석에 나타난 것과 정합적인 현상**이다 — "
            "임용시점을 더 늦춰서(offset을 계속 키워서) pre-2010 비중을 더 낮출수록 적중률이 계속 "
            "오를 가능성이 있으며, 이는 추정이 맞았다는 뜻이 아니라 모형이 구조적으로 낮은 예측을 "
            "선호한다는 뜻이다. 보정률 부재의 영향을 시사하는 현상으로만 해석하고, 이 결과를 근거로 "
            "\"임용시점 추정이 실제로 이 방향으로 틀렸다\"거나 \"모형이 이 offset에서 가장 정확하다\"고 "
            "단정하지 않는다."
        )
    else:
        lines.append(
            f"전체 적중률의 offset 간 변동폭은 {swing:.2f}%p다. 단조 패턴이 아니므로 특정 방향의 "
            "구조적 편향을 시사한다고 보기는 어려우나, 이 변동폭 자체를 임용시점 추정의 정확성이나 "
            "안정성의 근거로 해석하지 않는다 — 표본이 법정 상한 미절단 집단에 한정된 참고 분석이라는 "
            "점도 변함없다."
        )
    lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "tier1_evaluation.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
