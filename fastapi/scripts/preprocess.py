import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

RAW_FILE       = DATA_DIR / "SRM189138 통계자료 로우데이터(CSV) 추출.csv"
SEVERANCE_FILE = DATA_DIR / "퇴직수당금액.csv"

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


if __name__ == "__main__":
    process_active_income()
