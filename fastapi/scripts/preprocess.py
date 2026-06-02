import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
STATS_OUT_DIR = Path(__file__).parent / "stats_output"

RAW_FILE       = DATA_DIR / "SRM189138 통계자료 로우데이터(CSV) 추출.csv"
SEVERANCE_FILE = DATA_DIR / "퇴직수당금액.csv"

PENSION_FILE   = DATA_DIR / "연금급여 퇴직연금금액_컬럼추가.csv"
SEVERANCE_FILE2 = DATA_DIR / "퇴직수당금액_컬럼추가.csv"

OUT_ACTIVE = DATA_DIR / "active_income_stats.csv"


def bucket_months(months: pd.Series) -> pd.Series:
    bins = [0, 60, 120, 180, 240, 300, 360, float("inf")]
    labels = ["0~59", "60~119", "120~179", "180~239", "240~299", "300~359", "360+"]
    return pd.cut(months, bins=bins, right=False, labels=labels)


def agg_stats(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    return (
        df.groupby(group_col, observed=True)[value_col]
        .agg(
            평균="mean",
            중위값="median",
            p25=lambda x: x.quantile(0.25),
            p75=lambda x: x.quantile(0.75),
            count="count",
        )
        .reset_index()
        .rename(columns={group_col: "구간"})
    )


# ── 1. 로우데이터: 총승인월수 구간별 연금기준소득월액 통계 ──────────────────────
def process_active_income() -> pd.DataFrame:
    df = pd.read_csv(RAW_FILE, encoding="cp949")

    df = df[df["총승인월수"] > 0].copy()
    df["구간"] = bucket_months(df["총승인월수"])

    stats = agg_stats(df, "구간", "연금기준소득월액")
    stats.to_csv(OUT_ACTIVE, index=False, encoding="utf-8-sig")

    print("=== active_income_stats (총승인월수 구간별 연금기준소득월액) ===")
    print(stats.to_string(index=False))
    print(f"\n저장 완료: {OUT_ACTIVE}\n")
    return stats


def _load_retirement_base(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath, encoding="cp949")
    df["급여금액"] = df["급여금액"].abs()
    before = len(df)
    df = df[df["연령"] >= 18].copy()
    print(f"  음수/미성년 연령 제거: {before - len(df)}행 삭제 ({before} → {len(df)})")
    return df


def _agg_retirement(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["연령", "직종", "학교급"], observed=True)["급여금액"]
        .agg(
            평균="mean",
            중위값="median",
            p25=lambda x: x.quantile(0.25),
            p75=lambda x: x.quantile(0.75),
            count="count",
        )
        .reset_index()
    )


# ── 2. 퇴직연금 통계 ──────────────────────────────────────────────────────────
def process_retirement_pension() -> pd.DataFrame:
    STATS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STATS_OUT_DIR / "retirement_pension_stats.csv"

    df = _load_retirement_base(PENSION_FILE)
    df = df[df["급여명"] == "퇴직연금"].copy()

    stats = _agg_retirement(df)
    stats.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("=== retirement_pension_stats (연령·직종·학교급별 퇴직연금) ===")
    print(stats.head(5).to_string(index=False))
    print(f"\n저장 완료: {out_path}\n")
    return stats


# ── 3. 퇴직수당 통계 ──────────────────────────────────────────────────────────
def process_severance() -> pd.DataFrame:
    STATS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STATS_OUT_DIR / "severance_stats.csv"

    df = _load_retirement_base(SEVERANCE_FILE2)

    stats = _agg_retirement(df)
    stats.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("=== severance_stats (연령·직종·학교급별 퇴직수당) ===")
    print(stats.head(5).to_string(index=False))
    print(f"\n저장 완료: {out_path}\n")
    return stats


if __name__ == "__main__":
    process_active_income()
    process_retirement_pension()
    process_severance()
