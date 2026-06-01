import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
EDA_OUT_DIR = Path(__file__).parent / "eda_output"

PENSION_FILE = DATA_DIR / "연금급여 퇴직연금금액_컬럼추가.csv"


def _setup_korean_font():
    candidates = [
        "Malgun Gothic",
        "NanumGothic",
        "NanumBarunGothic",
        "AppleGothic",
        "UnDotum",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    else:
        # fallback: use any font containing "Gothic" or "Nanum"
        for f in fm.fontManager.ttflist:
            if "Gothic" in f.name or "Nanum" in f.name:
                plt.rcParams["font.family"] = f.name
                break
    plt.rcParams["axes.unicode_minus"] = False


def _load_pension() -> pd.DataFrame:
    df = pd.read_csv(PENSION_FILE, encoding="cp949")
    df["급여금액"] = df["급여금액"].abs()
    df = df[df["연령"] >= 18].copy()
    df = df[df["급여명"] == "퇴직연금"].copy()
    return df


# ── 그래프 1: 연도별 퇴직연금 수급자 수 추이 ────────────────────────────────
def plot_annual_recipients(df: pd.DataFrame):
    out = EDA_OUT_DIR / "01_annual_recipients.png"
    annual = df.groupby("년도").size().reset_index(name="수급자수")

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(data=annual, x="년도", y="수급자수", marker="o", ax=ax)
    ax.set_title("연도별 퇴직연금 수급자 수 추이 (2016~2024)")
    ax.set_xlabel("연도")
    ax.set_ylabel("수급자 수 (명)")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"저장: {out}")


# ── 그래프 2: 직종별 평균 퇴직연금 ──────────────────────────────────────────
def plot_by_occupation(df: pd.DataFrame):
    out = EDA_OUT_DIR / "02_by_occupation.png"
    grp = df.groupby("직종")["급여금액"].mean().reset_index()
    grp.columns = ["직종", "평균급여금액"]

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(data=grp, x="직종", y="평균급여금액", ax=ax)
    ax.set_title("직종별(교원/직원) 평균 퇴직연금")
    ax.set_xlabel("직종")
    ax.set_ylabel("평균 급여금액 (원)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"저장: {out}")


# ── 그래프 3: 학교급별 평균 퇴직연금 (내림차순) ─────────────────────────────
def plot_by_school_level(df: pd.DataFrame):
    out = EDA_OUT_DIR / "03_by_school_level.png"
    grp = (
        df.groupby("학교급")["급여금액"]
        .mean()
        .reset_index()
        .rename(columns={"급여금액": "평균급여금액"})
        .sort_values("평균급여금액", ascending=False)
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=grp, x="학교급", y="평균급여금액", order=grp["학교급"].tolist(), ax=ax)
    ax.set_title("학교급별 평균 퇴직연금 (내림차순)")
    ax.set_xlabel("학교급")
    ax.set_ylabel("평균 급여금액 (원)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"저장: {out}")


# ── 그래프 4: 연령대별(5세 단위) 수급자 분포 ────────────────────────────────
def plot_age_group_distribution(df: pd.DataFrame):
    out = EDA_OUT_DIR / "04_age_group_dist.png"
    df = df.copy()
    df["연령대_숫자"] = df["연령"] // 5 * 5
    df["연령대"] = df["연령대_숫자"].astype(str) + "대"
    grp = df.groupby("연령대_숫자").size().reset_index(name="수급자수")
    grp = grp.sort_values("연령대_숫자")
    grp["연령대"] = grp["연령대_숫자"].astype(str) + "대"

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.barplot(data=grp, x="연령대", y="수급자수", order=grp["연령대"].tolist(), ax=ax)
    ax.set_title("연령대별(5세 단위) 퇴직연금 수급자 분포")
    ax.set_xlabel("연령대")
    ax.set_ylabel("수급자 수 (명)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"저장: {out}")


if __name__ == "__main__":
    EDA_OUT_DIR.mkdir(parents=True, exist_ok=True)
    _setup_korean_font()

    df = _load_pension()
    print(f"퇴직연금 데이터 로드 완료: {len(df)}행\n")

    plot_annual_recipients(df)
    plot_by_occupation(df)
    plot_by_school_level(df)
    plot_age_group_distribution(df)

    print("\n모든 그래프 저장 완료.")
