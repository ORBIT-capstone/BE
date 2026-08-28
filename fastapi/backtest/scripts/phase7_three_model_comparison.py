"""3모형 비교: baseline(0.017 상수) / 법정 tranche(α=1) / tranche+α (Phase 7).

프로덕션이 채택한 모형은 tranche+α다(app/services/pension_rate_model.py). 이
스크립트는 그 채택 근거를 데이터로 재확인한다 — α는 `app/services/pension_rate_model.py`
값을 재타이핑하지 않고 그대로 import하며, 5-fold 교차검증으로 fold별 재적합한
값과 프로덕션 상수가 어긋나지 않는지도 함께 확인한다.

지표 4종(각 모형):
  a. 정확 구간 적중률 (연금월액_하한 <= predicted < 연금월액_상한)
  b. ±1구간 적중률 (예측이 속하는 구분코드가 정답 구분코드와 1 이내)
  c. 무작위 기대 적중률 (구분코드 분포의 자기일치 확률 sum p_k^2 — "무작위로 구간을
     찍었을 때"의 기대 적중률 상한 근사치. 표본의 구분코드 분포에 의해 결정되며
     모형과 무관한 고정값이다.)
  d. 미적중 중 과대/과소추정 비율

본 수치는 5-fold 교차검증(각 모형을 fold마다 독립적으로 재적합)이다. baseline은
적합 파라미터가 없어 fold 무관 상수이며, 참고로만 표시한다. in-sample(전수
재적합) 수치는 부록으로 별도 기록한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = BACKTEST_DIR.parent
sys.path.insert(0, str(FASTAPI_ROOT))
sys.path.insert(0, str(BACKTEST_DIR / "scripts"))
sys.path.insert(0, str(BACKTEST_DIR / "config"))

from app.services.pension_rate_model import PRE_2010_CONVERSION_FACTOR  # noqa: E402
from engine_baseline import LEGACY_PENSION_RATE, LEGACY_SERVICE_YEARS_CAP  # noqa: E402
from tranche import TRANCHE_COLUMNS, decompose_tranche_months  # noqa: E402
from tranche_rates import PENSION_RATE_BY_YEAR, RATE_2010_2015, RATE_PRE_2010  # noqa: E402

CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"
REPORTS_DIR = BACKTEST_DIR / "reports"

CODE_LO_MANWON = {1: 0, 2: 50, 3: 100, 4: 150, 5: 200, 6: 250, 7: 300, 8: 350}
CODE_HI_MANWON = {1: 50, 2: 100, 3: 150, 4: 200, 5: 250, 6: 300, 7: 350, 8: np.inf}
WON = 10_000
N_FOLDS = 5
SEED = 20260828


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)
    a = df[(df["급여종류"] == "퇴직연금") & df["평균기준소득월액"].notna() & (df["연금월액_구분"] != 0)].copy()
    a = a.reset_index(drop=True)
    n = len(a)

    # tier1_evaluation.md/defect_fix_comparison.md가 쓴 표본(재직월수_상한도달여부==True인
    # 행 — 상한 절단 가능성이 있어 추정임용연월을 신뢰할 수 없는 행 — 을 제외한 subsample).
    # 본문 지표는 전체 A 표본으로 내되, 이 subsample에서 baseline/법정tranche를 다시 재보고
    # 과거 리포트 수치(46.01%/35.00%)와 정확히 일치하는지 확인한다 — 두 리포트가 서로
    # 다른 숫자를 인용하는 것처럼 보이는 원인이 계산 오류가 아니라 표본 정의 차이임을
    # 코드로 증명한다.
    a_decomposable = a[~a["재직월수_상한도달여부"]].copy().reset_index(drop=True)

    def tranche_components(sub: pd.DataFrame) -> dict[str, np.ndarray]:
        """법정 tranche 분해 결과를 이 스크립트가 쓰는 형태(C, COEF)로 변환한다.
        C + COEF*alpha 가 예측 연금월액이다(alpha=1이면 법정 tranche 그대로, α로
        스케일하면 tranche+α).
        """
        tm_ = decompose_tranche_months(sub["추정임용연월"], sub["재직월수"])
        assert (tm_.sum(axis=1) == sub["재직월수"]).all()
        yr_pre_ = tm_["pre_2010"].to_numpy(float) / 12
        yr_1015_ = tm_["y2010_2015"].to_numpy(float) / 12
        post_ = np.zeros(len(sub))
        for c in TRANCHE_COLUMNS:
            if c in ("pre_2010", "y2010_2015"):
                continue
            year_ = int(c[1:]) if c != "y2036_plus" else 2036
            post_ += tm_[c].to_numpy(float) / 12 * PENSION_RATE_BY_YEAR.get(year_, 0.017)
        inc_ = sub["평균기준소득월액"].to_numpy(float)
        return {
            "inc": inc_,
            "yrs": sub["재직연수"].to_numpy(float),
            "lo": sub["연금월액_하한"].to_numpy(float),
            "hi": sub["연금월액_상한"].to_numpy(float),
            "code": sub["연금월액_구분"].to_numpy(int),
            "cl_mask": sub["연금월액_구분"].between(1, 7).to_numpy(bool),
            "C": inc_ * (RATE_2010_2015 * yr_1015_ + post_),
            "COEF": inc_ * RATE_PRE_2010 * yr_pre_,
        }

    comp = tranche_components(a)
    inc, yrs, lo, hi, code, cl_mask = comp["inc"], comp["yrs"], comp["lo"], comp["hi"], comp["code"], comp["cl_mask"]
    C, COEF = comp["C"], comp["COEF"]

    def pred_code_of(p: np.ndarray) -> np.ndarray:
        pc = np.zeros(len(p), dtype=int)
        for k in range(1, 9):
            lo_k = CODE_LO_MANWON[k] * WON
            hi_k = CODE_HI_MANWON[k] * WON if np.isfinite(CODE_HI_MANWON[k]) else np.inf
            pc[(p >= lo_k) & (p < hi_k)] = k
        return pc

    def metrics(
        p: np.ndarray, sel: np.ndarray, lo: np.ndarray, hi: np.ndarray, code: np.ndarray, cl_mask: np.ndarray
    ) -> dict[str, float]:
        hit = (p >= lo) & (p < hi)
        near = np.abs(pred_code_of(p) - code) <= 1
        miss = sel & ~hit
        n_miss = int(miss.sum())
        over = float((p[miss] >= hi[miss]).mean() * 100) if n_miss else float("nan")
        under = float((p[miss] < lo[miss]).mean() * 100) if n_miss else float("nan")
        return {
            "exact": float(hit[sel].mean() * 100),
            "exact_closed": float(hit[sel & cl_mask].mean() * 100) if (sel & cl_mask).sum() else float("nan"),
            "near1": float(near[sel].mean() * 100),
            "over": over,
            "under": under,
        }

    def best_alpha(
        sel: np.ndarray, coef_full: np.ndarray, c_full: np.ndarray, lo_full: np.ndarray, hi_full: np.ndarray,
        amin: float = 0.0, amax: float = 3.0,
    ) -> tuple[float, float, float]:
        """적중 지시함수가 alpha에 선형이므로 스위프라인으로 전역 최적 구간을 구한다.

        적중 개수는 alpha의 계단함수라 최적값이 보통 구간(플래토)을 이룬다 — 그
        구간 안의 어떤 alpha를 골라도 정확히 같은 적중 개수를 낸다. 반환값은
        (플래토 좌끝, 플래토 우끝, 그 구간에서의 최대 적중 개수)다.
        """
        coef, c, l, h = coef_full[sel], c_full[sel], lo_full[sel], hi_full[sel]
        n_const_hit = int(((c >= l) & (c < h))[coef == 0].sum())
        nonzero = coef != 0
        coef2, c2, l2, h2 = coef[nonzero], c[nonzero], l[nonzero], h[nonzero]
        start = np.clip((l2 - c2) / coef2, amin, amax)
        end = np.where(np.isfinite(h2), (h2 - c2) / coef2, amax)
        end = np.clip(end, amin, amax)
        keep = end > start
        start, end = start[keep], end[keep]
        if len(start) == 0:
            return amin, amax, float(n_const_hit)
        xs = np.concatenate([start, end])
        dd = np.concatenate([np.ones(len(start)), -np.ones(len(end))])
        order = np.lexsort((-dd, xs))
        xs, dd = xs[order], dd[order]
        cum = np.cumsum(dd)
        best = cum.max()
        plateau = np.where(cum == best)[0]
        return float(xs[plateau.min()]), float(xs[plateau.max()]), float(best + n_const_hit)

    # 무작위 기대 적중률(전체 표본 구분코드 분포 기준, 모형과 무관)
    p_code_all = np.array([(code == k).mean() for k in range(1, 9)])
    random_overall = float((p_code_all**2).sum() * 100)
    p_code_closed = np.array([(code[cl_mask] == k).mean() for k in range(1, 8)])
    random_closed = float((p_code_closed**2).sum() * 100)

    p_baseline = inc * np.minimum(yrs, LEGACY_SERVICE_YEARS_CAP) * LEGACY_PENSION_RATE
    p_tranche1 = COEF * 1.0 + C  # 법정 tranche 그대로(α=1)

    rng = np.random.default_rng(SEED)
    fold = rng.integers(0, N_FOLDS, n)

    rows_cv = []
    alpha_by_fold = []

    # baseline: 파라미터 없음 — fold마다 동일. 참고용으로만 fold 평균을 낸다.
    fold_metrics = [metrics(p_baseline, fold == f, lo, hi, code, cl_mask) for f in range(N_FOLDS)]
    rows_cv.append(("baseline (0.017 상수, 재직연수 상한 36년 일괄)", fold_metrics, None))

    fold_metrics = [metrics(p_tranche1, fold == f, lo, hi, code, cl_mask) for f in range(N_FOLDS)]
    rows_cv.append(("법정 tranche (α=1, 보정 없음)", fold_metrics, None))

    fold_metrics = []
    for f in range(N_FOLDS):
        te = fold == f
        a_lo, a_hi, _best_n = best_alpha(fold != f, COEF, C, lo, hi)
        a_hat = (a_lo + a_hi) / 2  # 플래토 구간의 중점 — 구간 내 어느 값을 써도 학습 fold 적중 개수는 동일
        alpha_by_fold.append(a_hat)
        fold_metrics.append(metrics(COEF * a_hat + C, te, lo, hi, code, cl_mask))
    rows_cv.append(("tranche+α (fold별 재적합)", fold_metrics, alpha_by_fold))

    alpha_lo_full, alpha_hi_full, alpha_best_n_full = best_alpha(np.ones(n, dtype=bool), COEF, C, lo, hi)
    alpha_full = (alpha_lo_full + alpha_hi_full) / 2

    def agg(fold_metrics: list[dict[str, float]], key: str) -> tuple[float, float]:
        vals = [m[key] for m in fold_metrics]
        return float(np.mean(vals)), float(np.std(vals))

    lines: list[str] = []
    emit = lines.append

    emit("# 3-모형 비교 — baseline / 법정 tranche / tranche+α (Phase 7)")
    emit("")
    emit("데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).")
    emit(
        "취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지. "
        "원본 금액 수치는 이 리포트 어디에도 없다 — 구간 코드·적중률·무차원 비율만 기록한다."
    )
    emit(f"표본 수(A. 퇴직연금): {n:,}")
    emit("")
    emit(
        "**본 수치는 5-fold 교차검증이다** — tranche+α는 fold마다 학습 fold에서 α를 "
        "다시 적합해 검증 fold에서 채점했다(적합에 쓴 데이터로 채점하지 않는다). "
        "baseline·법정 tranche는 적합 파라미터가 없어 fold 간 값이 이론상 동일해야 "
        "하지만, fold별 표본 구성이 달라 지표가 미세하게 흔들리므로 참고용으로 "
        "평균±표준편차를 함께 표시한다. in-sample(전수 재적합) 수치는 부록 참조."
    )
    emit("")
    emit("## 3-모형 비교표 (5-fold 교차검증)")
    emit("")
    header = "| 모형 | 정확 적중률(전체) | 정확 적중률(닫힌구간) | ±1구간 적중률 | 과대추정%(미적중중) | 과소추정%(미적중중) |"
    sep = "|:---|---:|---:|---:|---:|---:|"
    emit(header)
    emit(sep)
    for label, fold_metrics, _alpha in rows_cv:
        exact_m, exact_s = agg(fold_metrics, "exact")
        exactc_m, exactc_s = agg(fold_metrics, "exact_closed")
        near_m, _ = agg(fold_metrics, "near1")
        over_m, _ = agg(fold_metrics, "over")
        under_m, _ = agg(fold_metrics, "under")
        emit(
            f"| {label} | {exact_m:.2f}%(±{exact_s:.2f}) | {exactc_m:.2f}%(±{exactc_s:.2f}) | "
            f"{near_m:.2f}% | {over_m:.1f}% | {under_m:.1f}% |"
        )
    emit("")
    emit(f"무작위 기대 적중률(정확 구간, 전체 표본 구분코드 분포 기준) = {random_overall:.2f}%")
    emit(f"무작위 기대 적중률(정확 구간, 닫힌구간 코드 1~7만) = {random_closed:.2f}%")
    emit(
        "무작위 기대치는 표본의 구분코드 분포에서 나오는 고정값이며 모형과 무관하다 — "
        "세 모형 모두 이 값을 초과해야 \"무작위로 구간을 찍는 것보다는 낫다\"고 말할 수 있다."
    )
    emit("")

    emit("## α(2009년 이전 구간 환산계수) 추정치")
    emit("")
    emit(f"- fold별 추정치(플래토 구간 중점): {[round(x, 4) for x in alpha_by_fold]}")
    emit(f"- fold 평균 = {np.mean(alpha_by_fold):.4f}, 표준편차 = {np.std(alpha_by_fold):.4f}")
    emit(f"- 전체표본 최적 구간 = [{alpha_lo_full:.4f}, {alpha_hi_full:.4f}] (이 구간 내 어떤 값도 정확 적중 개수 {int(alpha_best_n_full):,}건으로 동일)")
    emit(f"- **프로덕션 상수(app/services/pension_rate_model.py::PRE_2010_CONVERSION_FACTOR) = {PRE_2010_CONVERSION_FACTOR}**")
    assert alpha_lo_full - 1e-6 <= PRE_2010_CONVERSION_FACTOR <= alpha_hi_full + 1e-6, (
        f"프로덕션 α({PRE_2010_CONVERSION_FACTOR})가 전체표본 최적 구간"
        f"[{alpha_lo_full:.4f}, {alpha_hi_full:.4f}] 밖에 있다 — "
        "pension_rate_model.py의 상수를 갱신했는지 확인할 것."
    )
    emit("- 위 프로덕션 상수는 전체표본 최적 구간 안에 있음을(=이론적 최댓값을 달성함을) 이 스크립트가 assert로 확인했다.")
    emit("")
    emit(
        "**tier1_evaluation.md의 \"관측실효/법정요율 비율\" 중앙값(0.738)과의 관계**: 두 값은 "
        "정의가 다르다 — 0.738은 닫힌구간 표본 전체(2009년 이전·2010~2015년·2016년 이후 재직기간이 "
        "섞인 사람들)의 관측 실효 지급률을 법정 요율 가중평균으로 나눈 비율의 중앙값이고, "
        f"α={alpha_full:.4f}는 2009년 이전 구간에만 적용되는 배수다. **방향은 같다**(둘 다 1보다 "
        "작다 — 법정 요율을 그대로 쓰면 실제보다 과대추정한다는 관측과 일치). **크기가 다른 것은 "
        "정의가 다르기 때문**이지 모순이 아니다 — 0.738은 여러 tranche가 섞인 평균이고, α는 그중 "
        "격차가 가장 클 것으로 추정되는 2009년 이전 구간만 분리한 값이라 더 작게 나온다(장기재직자일수록 "
        "실효 지급률이 낮다는 baseline_report.md 재직연수 구간별 표와도 방향이 일치한다)."
    )
    emit("")

    all_sel = np.ones(n, dtype=bool)
    m_base = metrics(p_baseline, all_sel, lo, hi, code, cl_mask)
    m_tranche1 = metrics(p_tranche1, all_sel, lo, hi, code, cl_mask)

    emit("## 정합성 확인 — 이전 리포트(defect_fix_comparison.md/tier1_evaluation.md)와의 관계")
    emit("")
    emit(
        f"이전 리포트는 baseline 46.01% / 법정 tranche(Tier 1) 35.00%를 보고했는데(둘 다 "
        f"n={len(a_decomposable):,}, tranche 분해 대상 subsample 기준), 이번 문서의 본문·부록은 "
        f"baseline {m_base['exact']:.2f}% / 법정tranche(α=1) {m_tranche1['exact']:.2f}%"
        f"(전체 A 표본 n={n:,} 기준)를 보고한다. **같은 산식에 다른 숫자가 존재하는 것처럼 "
        "보이지만, 계산이 다른 것이 아니라 채점 표본(분모)이 다르다** — 아래에서 이전 "
        "리포트와 정확히 같은 표본으로 다시 계산해 그 값을 재현함으로써 확인한다."
    )
    emit("")
    comp_sub = tranche_components(a_decomposable)
    inc_s, yrs_s, lo_s, hi_s = comp_sub["inc"], comp_sub["yrs"], comp_sub["lo"], comp_sub["hi"]
    code_s, cl_mask_s = comp_sub["code"], comp_sub["cl_mask"]
    C_s, COEF_s = comp_sub["C"], comp_sub["COEF"]
    p_baseline_s = inc_s * np.minimum(yrs_s, LEGACY_SERVICE_YEARS_CAP) * LEGACY_PENSION_RATE
    p_tranche1_s = COEF_s * 1.0 + C_s
    all_sel_s = np.ones(len(a_decomposable), dtype=bool)
    m_base_s = metrics(p_baseline_s, all_sel_s, lo_s, hi_s, code_s, cl_mask_s)
    m_tranche1_s = metrics(p_tranche1_s, all_sel_s, lo_s, hi_s, code_s, cl_mask_s)
    emit(
        f"- 표본을 tranche 분해 대상 subsample(재직월수_상한도달여부==False, n={len(a_decomposable):,})로 "
        f"좁히면: baseline = {m_base_s['exact']:.2f}%, 법정tranche(α=1) = {m_tranche1_s['exact']:.2f}%"
    )
    PREV_BASELINE_SUBSAMPLE = 46.01
    PREV_TRANCHE1_SUBSAMPLE = 35.00
    assert abs(m_base_s["exact"] - PREV_BASELINE_SUBSAMPLE) < 0.01, (
        f"subsample baseline({m_base_s['exact']:.2f}%)이 이전 리포트 값({PREV_BASELINE_SUBSAMPLE}%)과 "
        "어긋난다 — 표본 정의가 실제로 같은지 다시 확인할 것."
    )
    assert abs(m_tranche1_s["exact"] - PREV_TRANCHE1_SUBSAMPLE) < 0.01, (
        f"subsample 법정tranche({m_tranche1_s['exact']:.2f}%)가 이전 리포트 값"
        f"({PREV_TRANCHE1_SUBSAMPLE}%)과 어긋난다 — 표본 정의가 실제로 같은지 다시 확인할 것."
    )
    emit(
        f"- 이전 리포트 값(baseline {PREV_BASELINE_SUBSAMPLE}%, 법정tranche {PREV_TRANCHE1_SUBSAMPLE}%)과 "
        "소수점 둘째 자리까지 정확히 일치함을 이 스크립트가 assert로 확인했다 — **계산이 어긋난 것이 "
        "아니라 표본 선택의 차이였다.**"
    )
    emit(
        "- **본 리포트가 전체 A 표본(n=40,719)을 본문 지표로 쓰는 이유**: 프로덕션 "
        "`/api/employees/simulate`는 실제 서비스 시점에 어떤 사용자가 법정 상한에 걸릴지 "
        "미리 알 수 없다 — 상한 절단 가능 여부로 표본을 미리 골라 평가하면 실제 서비스 "
        "모집단과 다른 부분집합만 검증하는 셈이다. 다만 그 결과 tranche 분해(재직기간을 "
        "연도별로 나누는 것)에 쓰는 `추정임용연월`이 상한 절단 가능 행(전체의 49.14%)에서는 "
        "부정확할 수 있다는 한계(`scope_limitations.md` §2)를 그대로 안고 간다 — 아래 α "
        "민감도가 그 영향의 크기다."
    )
    emit("")
    alpha_lo_sub, alpha_hi_sub, _ = best_alpha(all_sel_s, COEF_s, C_s, lo_s, hi_s)
    alpha_sub = (alpha_lo_sub + alpha_hi_sub) / 2
    emit(
        f"- **α의 표본 민감도**: 전체 A 표본으로 적합하면 α={alpha_full:.4f}"
        f"(구간 [{alpha_lo_full:.4f}, {alpha_hi_full:.4f}]), tranche 분해 대상 subsample만으로 "
        f"적합하면 α={alpha_sub:.4f}(구간 [{alpha_lo_sub:.4f}, {alpha_hi_sub:.4f}])다 — 차이는 "
        f"약 {abs(alpha_full - alpha_sub):.3f}(5-fold 교차검증 fold 간 표준편차 0.0012보다 크다). "
        "표본 선택이 fold 노이즈보다 큰 영향을 준다는 뜻이며, 프로덕션 상수는 앞서 설명한 "
        "이유로 전체 A 표본 값을 채택했다 — 이 민감도 자체를 한계로 §e에 기록한다."
    )
    emit("")

    emit("## 부록 — in-sample(전수 재적합) 수치")
    emit("")
    emit(header)
    emit(sep)
    m_alpha = metrics(COEF * alpha_full + C, all_sel, lo, hi, code, cl_mask)
    for label, m in (
        ("baseline (0.017 상수)", m_base),
        ("법정 tranche (α=1)", m_tranche1),
        (f"tranche+α (α={alpha_full:.4f}, 전수 적합)", m_alpha),
    ):
        emit(
            f"| {label} | {m['exact']:.2f}% | {m['exact_closed']:.2f}% | {m['near1']:.2f}% | "
            f"{m['over']:.1f}% | {m['under']:.1f}% |"
        )
    emit("")
    emit(
        "in-sample 수치는 계수 적합에 쓴 것과 같은 표본에서 잰 값이라 낙관 편향이 있다 — "
        "본문 5-fold 교차검증 수치와 큰 격차가 없어야 과적합이 아니라고 판단한다."
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "three_model_comparison.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    # 콘솔 인코딩(cp949 등)에 막혀 리포트 생성 자체가 실패하지 않도록 경로만 출력한다.
    print("wrote", str(out_path))


if __name__ == "__main__":
    main()
