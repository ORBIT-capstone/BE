"""급여종류별 검증 가능성 판정 (Phase 2).

각 급여종류를 A~F로 분류하고, 행수 / 입력값(평균기준소득월액·재직월수) 보유율 /
정답 구간(해당 급여종류에 대응하는 금액구분코드가 0이 아닌 비율) 보유율을 표로 출력한다.

D(퇴직일시금)·E(퇴직수당)는 평균기준소득월액이 전 행 결측이라 엔진 입력값이 없다.
대체값을 만들지 않고 "입력변수 미제공으로 검증 불가"로 명시한다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BACKTEST_DIR = Path(__file__).resolve().parent.parent
CLEAN_FILE = BACKTEST_DIR / "data" / "clean" / "backtest_clean.parquet"

# 카테고리 -> (급여종류 값 목록, 정답 구분 컬럼 목록)
CATEGORIES: dict[str, tuple[list[str], list[str]]] = {
    "A. 퇴직연금": (["퇴직연금"], ["연금월액_구분"]),
    "B. 조기퇴직연금": (["조기퇴직연금"], ["연금월액_구분"]),
    "C. 퇴직연금공제일시금": (["퇴직연금공제일시금"], ["연금월액_구분", "일시금금액_구분"]),
    "D. 퇴직일시금": (["퇴직일시금"], ["일시금금액_구분"]),
    "E. 퇴직수당": (["퇴직수당"], ["수당금액_구분"]),
}

F_LABEL = "F. 그 외(유족·분할·연계·장해 등, scope 밖)"

MIN_CELL = 5  # n < 5 그룹은 마스킹


def _mask(n: int) -> str:
    return "n<5 (마스킹)" if n < MIN_CELL else f"{n:,}"


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    covered_types: set[str] = set()

    for label, (types, answer_cols) in CATEGORIES.items():
        sub = df[df["급여종류"].isin(types)]
        covered_types |= set(types)
        n = len(sub)
        income_rate = sub["평균기준소득월액"].notna().mean() * 100 if n else float("nan")
        months_rate = sub["재직월수"].notna().mean() * 100 if n else float("nan")
        answer_rates = {
            col: (sub[col] > 0).mean() * 100 if n else float("nan") for col in answer_cols
        }
        verifiable = "가능" if (income_rate > 0 and months_rate > 0) else "불가 (입력변수 미제공)"
        rows.append(
            {
                "카테고리": label,
                "행수": _mask(n),
                "평균기준소득월액_보유율(%)": round(income_rate, 2),
                "재직월수_보유율(%)": round(months_rate, 2),
                "정답구간_보유율(%)": {k: round(v, 2) for k, v in answer_rates.items()},
                "검증가능여부": verifiable,
            }
        )

    other = df[~df["급여종류"].isin(covered_types)]
    n_other = len(other)
    rows.append(
        {
            "카테고리": F_LABEL,
            "행수": _mask(n_other),
            "평균기준소득월액_보유율(%)": None,
            "재직월수_보유율(%)": None,
            "정답구간_보유율(%)": None,
            "검증가능여부": "제외 (엔진 scope 밖)",
        }
    )

    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(CLEAN_FILE)
    summary = build_summary(df)

    total = len(df)
    categorized_total = sum(
        len(df[df["급여종류"].isin(types)]) for types, _ in CATEGORIES.values()
    )
    other_total = total - categorized_total
    assert categorized_total + other_total == total

    print(f"전체 행수: {total:,}")
    print(summary.to_string(index=False))
    print()
    print("D(퇴직일시금)·E(퇴직수당): 평균기준소득월액 보유율 0% -> 입력변수 미제공으로 검증 불가")


if __name__ == "__main__":
    main()
