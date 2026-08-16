"""사학연금법상 퇴직급여 산정 재직기간 상한(개월) 판정.

# 근거: 사립학교교직원 연금법 부칙(법률 제13561호, 2015.12.15 공포)
#       제11조(재직기간 상한 연장에 관한 경과조치)
#       "제44조제3항, 제42조제1항에 따라 준용되는 「공무원연금법」
#        제46조제4항·제5항의 개정규정에도 불구하고 이 법 시행 당시
#        재직 중인 교직원(…제32조제1항에 따라 합산한 사람을 포함한다)의
#        퇴직급여 산정 시 재직기간과 부담금 납부기간은 다음 각 호의
#        연수를 초과할 수 없다."
#       1호 21년 이상: 33년 / 2호 17~21년 미만: 34년
#       3호 15~17년 미만: 35년 / 4호 15년 미만: 36년
# 확인일자: 2026-08-16 (법제처 국가법령정보센터 원문)

주의(퇴직급여 산정 전용): 제11조는 "퇴직급여 산정 시" 재직기간에만 적용된다.
퇴직수당은 별개 급여이므로 이 테이블과 무관하다 — 퇴직수당 상한(33년)은
`employees_service.py`의 `SEVERANCE_YEARS_CAP`에 별개 상수로 분리돼 있다.
두 상수를 하나로 통합하지 말 것.

주의(적용 대상): 제11조 경과조치는 "이 법 시행 당시(2016.1.1) 재직 중인 교직원"에게만
적용된다. 2016.1.1 이후 신규 임용자는 경과조치 대상이 아니라 본칙(제44조제3항,
그리고 이 조가 준용하는 공무원연금법 제46조제4항·제5항)에 따라 36년이 적용된다 —
결과값은 경과조치 4호(15년 미만 → 36년)와 같지만 적용 근거 조문이 다르므로,
아래 `resolve_pension_service_cap_months`는 이 둘을 cap_basis로 구분해 반환한다.

주의(재직기간의 정의): 제11조는 "제32조제1항에 따라 합산한 사람을 포함한다"고
명시한다 — 즉 여기서 말하는 "이 법 시행 전의 재직기간"은 캘린더상 실제 근무기간이
아니라 군복무 소급이나 경력합산·소급통산이 반영된 "인정 재직기간"이다. 이는
`fastapi/backtest/`가 원본 데이터의 `재직월수`를 다룰 때 이미 명시한 "인정 재직기간"
한계(`build_clean_dataset.py` 한계 2, `scope_limitations.md` §2-1)와 정확히 같은
개념이다. `service_months_as_of_2016`을 임용연월(또는 그 추정치)로부터 역산하는
쪽에서는 이 값이 근사치일 수밖에 없다는 점을 함께 인지할 것.
"""

from __future__ import annotations

# 경과조치(제11조) 표: (하한_개월수, 상한_개월수) — 하한 개월수 이상이면 해당 상한 적용.
# 내림차순으로 순회하며 첫 매치를 사용한다. 21년=252개월, 17년=204개월, 15년=180개월.
_STATUTORY_TIERED_CAP_MONTHS: list[tuple[int, int]] = [
    (252, 396),  # 21년 이상 -> 33년
    (204, 408),  # 17년 이상 21년 미만 -> 34년
    (180, 420),  # 15년 이상 17년 미만 -> 35년
    (1, 432),  # 15년 미만(1개월 이상) -> 36년
]

# 본칙(제44조제3항, 준용 공무원연금법 제46조제4항·제5항) 상 상한 — 36년.
# service_months_as_of_2016 == 0(경과조치 비대상) 또는 미제공(None, 판정 불가) 시 폴백.
DEFAULT_MAX_CAP_MONTHS = 432


def resolve_pension_service_cap_months(
    service_months_as_of_2016: int | None,
) -> tuple[int, str]:
    """2016.1.1 시점 인정 재직월수로 퇴직급여 산정 재직기간 상한(개월)을 판정한다.

    반환: (상한_개월수, cap_basis)
      - "STATUTORY_TIERED": 2016.1.1 당시 재직 중이었음(service_months_as_of_2016 > 0)
        -> 부칙 제11조 경과조치 표(33/34/35/36년 차등) 적용.
      - "STATUTORY_DEFAULT": service_months_as_of_2016 == 0
        -> 2016.1.1 이후 임용자, 경과조치 비대상 -> 본칙 36년 적용.
        (값은 STATUTORY_TIERED의 4호와 같지만 근거 조문이 다르다.)
      - "DEFAULT_MAX": service_months_as_of_2016 미제공(None) -> 판정 불가.
        기존 동작(일괄 36년) 유지를 위한 폴백.

    경계 판정은 월 단위 정수 비교로만 수행한다(연 단위 반올림 금지).
    """
    if service_months_as_of_2016 is None:
        return DEFAULT_MAX_CAP_MONTHS, "DEFAULT_MAX"

    if service_months_as_of_2016 < 0:
        raise ValueError("service_months_as_of_2016은 0 이상이어야 합니다.")

    if service_months_as_of_2016 == 0:
        return DEFAULT_MAX_CAP_MONTHS, "STATUTORY_DEFAULT"

    for lower_bound_months, cap_months in _STATUTORY_TIERED_CAP_MONTHS:
        if service_months_as_of_2016 >= lower_bound_months:
            return cap_months, "STATUTORY_TIERED"

    raise AssertionError("unreachable: 마지막 구간(1개월 이상)이 항상 매칭되어야 함")
