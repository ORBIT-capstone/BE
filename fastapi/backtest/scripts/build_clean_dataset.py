"""사학연금 퇴직급여신청자 원본 마이크로데이터를 정제해 분석용 parquet으로 만든다.

데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터
             (backtest/data/raw/, 194,315행, 퇴직일 2020-01~2025-01)

취급 제한 (제공기관 사후 공지):
  1. 학교명 삭제
  2. 금액(연금월액·수당금액·일시금금액)은 원본값이 아니라 구간값으로만 사용
  3. 프로젝트 목적 외 사용 금지, 외부 노출 금지
이 스크립트는 위 규칙에 따라 원본 금액·기관 식별 컬럼을 전부 제거하고,
구간 코드만 원 단위 하한/상한으로 변환해 남긴다.

한계 (반드시 인지하고 사용할 것):
  1. `재직월수`는 실제 재직 캘린더 기간이 아니라 "인정 재직기간"이다. 군복무 소급이나
     임용 전 경력합산이 포함되면 실제 임용시점과 어긋난다.
  2. `재직월수`가 법정 상한값(396/408/420/432개월 = 33/34/35/36년)과 정확히 일치하는
     행은 사학연금법 부칙(법률 제13561호)의 재직기간 상한(2016.1.1 시점 재직기간에 따라
     21년 이상→33년, 17~21년→34년, 15~17년→35년, 15년 미만→36년) 적용 결과일 수 있다.
     실제 재직기간은 이보다 길 수 있으므로, 이 행들의 `추정임용연월`은 실제보다 늦게
     추정된다. `재직월수_상한도달여부`는 이 네 값과의 **정확한 일치**로만 판정한다 —
     예: 398개월은 어느 법정 상한값도 아니므로 절단으로 간주하지 않는다.
  3. `추정임용연월`은 `재직월수`가 퇴직월 자체를 포함하지 않는다고 가정한다 — 즉 근무
     구간을 `[추정임용연월, 퇴직연월 - 1개월]`(재직월수만큼의 길이)로 역산한다. 만약
     실제 인정 재직기간이 퇴직월을 포함하는 방식으로 집계된다면 이 스크립트의
     `추정임용연월`은 실제보다 1개월 이르게 추정된다. 사학연금공단의 재직월수 집계
     방식을 확인하지 못해 이 관례를 확정값이 아닌 가정으로 문서화해 둔다
     (tests/test_build_clean_dataset.py::test_estimate_appointment_yyyymm_off_by_one_convention
     이 현재 동작을 고정한다).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from interval_utils import (  # noqa: E402
    ALLOWANCE_BOUNDS_MANWON,
    LUMPSUM_BOUNDS_MANWON,
    PENSION_BOUNDS_MANWON,
    bounds_to_won_maps,
)

BACKTEST_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BACKTEST_DIR / "data" / "raw"
CLEAN_DIR = BACKTEST_DIR / "data" / "clean"

RAW_FILE = RAW_DIR / "2. (신정우 학생 양식)퇴직급여신청자 자료 추출_V1.xlsx"
CLEAN_FILE = CLEAN_DIR / "backtest_clean.parquet"

SHEET_NAME = "Sheet1"
SKIPROWS = 4

DELETED_COLUMNS = ["증서번호", "기관명", "기관주소", "연금월액", "수당금액", "일시금금액"]

# 사학연금법 부칙(법률 제13561호) — 2016.1.1 시점 재직기간별 재직연수 상한(년) x 12.
# 21년 이상 재직자->33년(396개월), 17~21년->34년(408개월), 15~17년->35년(420개월),
# 15년 미만->36년(432개월). 이 네 값과 정확히 일치하는 재직월수만 "상한 절단 가능성
# 있음"으로 플래그한다 — 예: 398개월은 이 집합의 원소가 아니므로 절단으로 보지 않는다.
STATUTORY_CAP_MONTHS = {396, 408, 420, 432}


def _yyyymmdd_to_yyyymm(series: pd.Series) -> pd.Series:
    """YYYYMMDD 정수 컬럼에서 일(day) 단위를 버리고 YYYYMM 정수로 변환한다."""
    return (series // 100).astype("int64")


def _estimate_appointment_yyyymm(퇴직연월: pd.Series, 재직월수: pd.Series) -> pd.Series:
    """추정임용연월을 월 단위 정수 연산으로 계산한다 (날짜 라이브러리 사용 금지).

    total = 퇴직연도 * 12 + (퇴직월 - 1)
    start = total - 재직월수
    추정임용연월 = (start // 12, start % 12 + 1)
    """
    year = 퇴직연월 // 100
    month = 퇴직연월 % 100
    total = year * 12 + (month - 1)
    start = total - 재직월수
    est_year = start // 12
    est_month = start % 12 + 1
    return (est_year * 100 + est_month).astype("int64")


def _is_service_months_capped(재직월수: pd.Series) -> pd.Series:
    """재직월수가 사학연금법 부칙상 재직기간 상한값(STATUTORY_CAP_MONTHS)과 정확히
    일치하는지 판정한다. 실제 재직기간이 이보다 길었을 수 있는(=상한 절단 가능성이
    있는) 행을 표시하는 것이며, 그 자체가 "절단이 확정됐다"는 뜻은 아니다.
    """
    return 재직월수.isin(STATUTORY_CAP_MONTHS)


def build_clean_dataset() -> pd.DataFrame:
    raw = pd.read_excel(RAW_FILE, sheet_name=SHEET_NAME, skiprows=SKIPROWS)

    clean = pd.DataFrame(index=raw.index)

    clean["매핑키값"] = raw["매핑키값"]
    clean["퇴직연월"] = _yyyymmdd_to_yyyymm(raw["퇴직일"])
    clean["급여처리연월"] = _yyyymmdd_to_yyyymm(raw["급여처리일"])
    clean["퇴직당시연령"] = raw["퇴직당시연령"]
    clean["기관소재지역"] = raw["기관소재지역"]
    clean["학교급"] = raw["학교급"]
    clean["직구분"] = raw["직구분"]
    clean["급여종류"] = raw["급여종류"]
    clean["재직월수"] = raw["재직월수"]
    clean["재직연수"] = raw["재직월수"] / 12
    clean["연금개시연월"] = raw["연금개시연월"]
    clean["평균기준소득월액"] = raw["평균기준소득월액"]

    clean["연금월액_구분"] = raw["연금월액_구분"]
    clean["수당금액_구분"] = raw["수당금액_구분"]
    clean["일시금금액_구분"] = raw["일시금금액_구분"]

    pension_lo, pension_hi = bounds_to_won_maps(PENSION_BOUNDS_MANWON)
    allowance_lo, allowance_hi = bounds_to_won_maps(ALLOWANCE_BOUNDS_MANWON)
    lumpsum_lo, lumpsum_hi = bounds_to_won_maps(LUMPSUM_BOUNDS_MANWON)

    clean["연금월액_하한"] = clean["연금월액_구분"].map(pension_lo)
    clean["연금월액_상한"] = clean["연금월액_구분"].map(pension_hi)
    clean["수당금액_하한"] = clean["수당금액_구분"].map(allowance_lo)
    clean["수당금액_상한"] = clean["수당금액_구분"].map(allowance_hi)
    clean["일시금금액_하한"] = clean["일시금금액_구분"].map(lumpsum_lo)
    clean["일시금금액_상한"] = clean["일시금금액_구분"].map(lumpsum_hi)

    clean["추정임용연월"] = _estimate_appointment_yyyymm(clean["퇴직연월"], clean["재직월수"])
    clean["재직월수_상한도달여부"] = _is_service_months_capped(clean["재직월수"])

    assert not (set(DELETED_COLUMNS) & set(clean.columns)), (
        f"삭제 대상 컬럼이 정제 데이터셋에 남아있음: {set(DELETED_COLUMNS) & set(clean.columns)}"
    )

    return clean


def main() -> None:
    clean = build_clean_dataset()
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(CLEAN_FILE, index=False)

    print(f"정제 완료: {len(clean):,}행 / {len(clean.columns)}컬럼 -> {CLEAN_FILE}")
    print(f"재직월수_상한도달여부 True 비율: {clean['재직월수_상한도달여부'].mean() * 100:.2f}%")


if __name__ == "__main__":
    main()
