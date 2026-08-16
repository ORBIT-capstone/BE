"""백테스트 원천 데이터 탐색 스크립트.

backtest/data/ 아래 3개 원천 파일(퇴직연금금액, 퇴직수당금액, 기준정보)의
행 수 / 결측치 / 고유값 분포를 확인하고, 개인 식별자가 없을 경우
년도x연령x지역x학교급x직종 세그먼트로 파일 간 매칭 가능 비율을 계산한다.

실행: python backtest/scripts/explore_data.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backtest/
DATA_DIR = os.path.join(BASE_DIR, "data")

PENSION_CSV = os.path.join(DATA_DIR, "연금급여 퇴직연금금액_컬럼추가.csv")
SEVERANCE_CSV = os.path.join(DATA_DIR, "퇴직수당금액_컬럼추가.csv")
BASELINE_XLSX = os.path.join(DATA_DIR, "SRM189424 [SRM189138]에 관련한 추가 요청.xlsx")

pd.set_option("display.max_rows", 300)
pd.set_option("display.width", 200)


def load_pension() -> pd.DataFrame:
    return pd.read_csv(PENSION_CSV, encoding="cp949", dtype=str)


def load_severance() -> pd.DataFrame:
    return pd.read_csv(SEVERANCE_CSV, encoding="cp949", dtype=str)


def load_baseline() -> pd.DataFrame:
    return pd.read_excel(BASELINE_XLSX, sheet_name="Sheet1", dtype=str)


def section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def profile_df(name: str, df: pd.DataFrame) -> None:
    section(f"[1] {name} - 기본 프로파일 (행 수: {len(df):,})")
    profile = pd.DataFrame(
        {
            "결측치": df.isna().sum(),
            "결측치(%)": (df.isna().mean() * 100).round(3),
            "고유값 수": df.nunique(dropna=True),
        }
    )
    print(profile)


def unique_values(name: str, df: pd.DataFrame) -> None:
    section(f"[2] {name} - 급여종류/급여명 고유값")
    if not {"급여종류", "급여명"}.issubset(df.columns):
        print("급여종류/급여명 컬럼 없음")
        return
    mapping = df[["급여종류", "급여명"]].drop_duplicates().sort_values(["급여종류", "급여명"])
    print(f"급여종류 고유값 수: {df['급여종류'].nunique()}, 급여명 고유값 수: {df['급여명'].nunique()}")
    print(mapping.to_string(index=False))
    print("\n급여명별 건수:")
    print(df["급여명"].value_counts())


def amount_distribution(name: str, df: pd.DataFrame, col: str) -> None:
    section(f"[3] {name} - {col} 분포 (단위 추정용)")
    amounts = pd.to_numeric(df[col], errors="coerce")
    n_fail = amounts.isna().sum() - df[col].isna().sum()
    print(f"결측치: {df[col].isna().sum():,} / 숫자 변환 실패(결측 제외): {n_fail:,} / 전체: {len(amounts):,}")
    print(amounts.describe(percentiles=[0.25, 0.5, 0.75]))
    neg = (amounts < 0).sum()
    print(f"음수 건수: {neg:,} ({neg / len(amounts) * 100:.2f}%)")


def age_year_profile(name: str, df: pd.DataFrame, year_col: str, age_col: str) -> None:
    section(f"[4] {name} - {year_col}/{age_col} 형식 확인")
    ages_numeric = pd.to_numeric(df[age_col], errors="coerce")
    non_numeric_ages = df.loc[ages_numeric.isna() & df[age_col].notna(), age_col].unique()
    print(f"{age_col}: 숫자 변환 불가 고유값 (구간형 등, 최대 20개 표시) -> {non_numeric_ages[:20]}")
    print(f"{age_col} 숫자 변환 성공 범위: min={ages_numeric.min()}, max={ages_numeric.max()}")

    years_numeric = pd.to_numeric(df[year_col], errors="coerce")
    non_numeric_years = df.loc[years_numeric.isna() & df[year_col].notna(), year_col].unique()
    print(f"{year_col}: 숫자 변환 불가 고유값 -> {non_numeric_years[:20]}")
    print(f"{year_col} 범위: min={years_numeric.min()}, max={years_numeric.max()}, 고유값={sorted(years_numeric.dropna().unique())}")


def _normalize_segment_cols(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """서로 다른 파일의 컬럼명을 공통 세그먼트 키(년도/연령/지역/학교급/직종)로 정규화."""
    renamed = df.rename(columns=col_map)[list(col_map.values())].copy()
    for col in ("년도", "연령"):
        renamed[col] = pd.to_numeric(renamed[col], errors="coerce")
    for col in ("지역", "학교급", "직종"):
        renamed[col] = renamed[col].astype(str).str.strip()
    return renamed


def category_label_diff(pension: pd.DataFrame, baseline_norm: pd.DataFrame) -> None:
    section("[5] 카테고리 라벨 일치 여부 확인 (매칭 전 선행 점검)")
    for col in ("지역", "학교급", "직종"):
        a = set(pension[col].dropna().unique())
        b = set(baseline_norm[col].dropna().unique())
        only_a = a - b
        only_b = b - a
        print(f"- {col}: 퇴직연금금액에만 있음={sorted(only_a)} / 기준정보에만 있음={sorted(only_b)}")


def identifier_check(dfs: dict[str, pd.DataFrame]) -> None:
    section("[5] 개인 단위 식별자 존재 여부 확인")
    for name, df in dfs.items():
        print(f"- {name} 컬럼 목록: {list(df.columns)}")
    print("-> 3개 파일 모두 주민번호/사번 등 개인 식별자 컬럼이 없음. 개인 단위 조인 불가능.")


def linkage_check(pension: pd.DataFrame, baseline: pd.DataFrame) -> None:
    section("[6] 세그먼트(년도x연령x지역x학교급x직종) 매칭 비율 - 파일①(퇴직연금금액) vs 파일③(기준정보)")

    pension_norm = _normalize_segment_cols(
        pension, {"년도": "년도", "연령": "연령", "지역": "지역", "학교급": "학교급", "직종": "직종"}
    )
    baseline_norm = _normalize_segment_cols(
        baseline,
        {
            "기준년도": "년도",
            "기준년도기준연령": "연령",
            "지역": "지역",
            "학교급정보": "학교급",
            "직구분": "직종",
        },
    )

    category_label_diff(pension_norm, baseline_norm)

    seg_cols = ["년도", "연령", "지역", "학교급", "직종"]
    a_segments = pension_norm.dropna(subset=seg_cols).drop_duplicates(subset=seg_cols)[seg_cols]
    b_segments = baseline_norm.dropna(subset=seg_cols).drop_duplicates(subset=seg_cols)[seg_cols]

    merged = a_segments.merge(b_segments, on=seg_cols, how="inner")

    n_a = len(a_segments)
    n_b = len(b_segments)
    n_matched = len(merged)

    print(f"\n파일① 고유 세그먼트 수: {n_a:,}")
    print(f"파일③ 고유 세그먼트 수: {n_b:,}")
    print(f"양쪽에 모두 존재하는 세그먼트 수: {n_matched:,}")
    print(f"파일① 기준 매칭률 (매칭/①): {n_matched / n_a * 100:.2f}%")
    print(f"파일③ 기준 매칭률 (매칭/③): {n_matched / n_b * 100:.2f}%")

    # 행(레코드) 기준으로도 참고용 매칭률 계산 (세그먼트가 아니라 원본 row 커버리지)
    pension_rows_matched = pension_norm.dropna(subset=seg_cols).merge(b_segments, on=seg_cols, how="inner")
    print(
        f"참고: 파일① 전체 행 중 매칭 세그먼트에 속하는 행 비율 "
        f"= {len(pension_rows_matched):,} / {len(pension_norm):,} "
        f"({len(pension_rows_matched) / len(pension_norm) * 100:.2f}%)"
    )


def main() -> None:
    pension = load_pension()
    severance = load_severance()
    baseline = load_baseline()

    profile_df("① 퇴직연금금액", pension)
    profile_df("② 퇴직수당금액", severance)
    profile_df("③ 기준정보", baseline)

    unique_values("① 퇴직연금금액", pension)
    unique_values("② 퇴직수당금액", severance)

    amount_distribution("① 퇴직연금금액", pension, "급여금액")
    amount_distribution("② 퇴직수당금액", severance, "급여금액")
    amount_distribution("③ 기준정보", baseline, "연금기준소득월액")

    age_year_profile("① 퇴직연금금액", pension, "년도", "연령")
    age_year_profile("② 퇴직수당금액", severance, "년도", "연령")
    age_year_profile("③ 기준정보", baseline, "기준년도", "기준년도기준연령")

    identifier_check({"① 퇴직연금금액": pension, "② 퇴직수당금액": severance, "③ 기준정보": baseline})

    linkage_check(pension, baseline)


if __name__ == "__main__":
    main()
