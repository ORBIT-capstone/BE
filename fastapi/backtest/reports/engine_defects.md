# Engine Defects — 백테스트로 확인된 현재 엔진 결함/관찰 목록

데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).
취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지.
원본 금액 수치는 이 리포트 어디에도 없다.

**이 리포트는 결함 기록용이며, 이번 트랙에서는 `fastapi/app/` 이하 코드를 수정하지 않는다.**
엔진 수정은 법령 확인 후 별도 이슈로 진행한다.

---

## 1. [해결됨] 재직연수 상한 일괄 36년 캡

- **위치**: `fastapi/app/services/employees_service.py::simulate_employees`
  ```python
  pension_years = min(retire_months / 12, 36)  # 수정 전
  ```
- **문제**: 사학연금법 부칙(법률 제13561호) 제11조는 2016.1.1 시점 재직기간에 따라 상한을
  차등 적용한다 — 21년 이상 재직자 33년, 17~21년 34년, 15~17년 35년, 15년 미만 36년
  (2016.1.1 이후 임용자만 본칙 36년). 수정 전 엔진은 이 구분 없이 모든 사용자에게
  36년 상한을 적용했다.
- **조치**: `fastapi/app/services/service_cap_rules.py`(신설)에 부칙 제11조 경과조치
  표를 외부화하고, `simulate_employees`가 신규 옵셔널 입력
  `SimulateRequest.service_months_as_of_2016`(2016.1.1 시점 인정 재직월수)으로
  33/34/35/36년 중 하나를 판정하도록 교체했다(`resolve_pension_service_cap_months`,
  `cap_basis` 응답 필드로 판정 근거 노출). 입력을 생략하면 기존 동작(36년 고정,
  `cap_basis=DEFAULT_MAX`)과 완전히 동일하다(하위 호환).
  퇴직수당 상한(33년, `SEVERANCE_YEARS_CAP`)은 별개 규정이라 이 테이블과 분리했다
  (통합 금지 경고 주석 포함).
- **[중요] 이 결함은 백테스트 데이터로 검증 불가능하다 — "영향 미미"가 아니라
  "측정 불가"다.** `defect_fix_comparison.md`에서 수정 전/후를 실측 비교한 결과,
  A(퇴직연금) 표본 40,719행 중 예측값이 달라진 행은 **3행뿐**이었다(전체 적중률
  43.54% -> 43.54%, 변화 없음. tranche 부분표본 20,708행 기준 1행만 변경, 46.01% ->
  46.01%). 원인은 공단이 제공한 `재직월수`가 **이미 법정 상한이 적용된 인정
  재직기간**이기 때문이다 — A 표본 전체에서 396개월을 초과하는 행이 이 3건뿐이고
  그중 2건은 그 자체로 법정 상한값(408=34년)과 일치한다(`scope_limitations.md`
  §2, §2-3 참조). 즉 엔진의 상한 로직이 발동할 여지가 이 표본 안에는 구조적으로
  거의 없다 — 표본을 늘려도 이 결함의 영향을 **이 데이터로는 측정할 수 없다.**
  반면 서비스 경로(`/api/employees/simulate`)는 사용자가 상한 미적용 재직연수를
  직접 입력하므로 결함이 실재했고, 수정 효과는 백테스트가 아니라
  `tests/test_employees_service.py`의 경계값 단위테스트로 확인했다. 애초 이 항목이
  "baseline의 압도적 과대추정(98.00%)의 방향과 일치한다"고 서술했던 것은 상관관계를
  인과관계로 오인한 것이었다 — 과대추정의 실제 원인은 보정률·소득재분배 등 여전히
  미구현인 요소들 쪽에 있다고 봐야 한다(`tier1_evaluation.md` 결론과 정합).
- **근거**: `baseline_report.md`(수정 전 스냅샷), `defect_fix_comparison.md`(수정
  전/후 비교, 표 A·B, 예측값이 바뀐 3행의 특성 각주).
- **테스트**: `tests/test_employees_service.py`(경계값 179/180/181, 203/204/205,
  251/252/253개월 포함 22개 테스트) + 기존 golden snapshot 재생성(값 변화 없음,
  응답 필드 2개 추가만 반영).
- **커밋**: `3fe37dc` — 🐛 Fix: 연금 산정 재직기간 상한 차등 적용 (사학연금법 부칙 제11조)

---

## 1-1. [해결됨, 관련 결함] LUMP_SUM/SPLIT 경로 재직기간 상한 누락

- **위치**: `fastapi/app/services/retirement_service.py::_calculate_lump_sum_and_pension`
  ```python
  pension_years = total_service_years - deduction_years  # 수정 전, 상한 없음
  ```
- **문제**: `ScenariosRequest.total_service_years`는 스키마상 최대 100년까지 입력
  가능한데(`Field(ge=10, le=100)`), LUMP_SUM/SPLIT(공제일시금) 계산 경로에는 재직기간
  상한 자체가 없었다 — #1 조사 중 함께 발견한 결함으로, 원래 §4 "참고" 항목이었다.
- **조치**: `resolve_pension_service_cap_months(None)`(이 엔드포인트는
  `service_months_as_of_2016` 입력 필드가 없어 항상 DEFAULT_MAX=36년)로 상한을 구해
  `min(total_service_years, cap) - deduction_years` 순서로 적용했다 — **캡을 공제
  전에 적용**한다. 순서가 바뀌면(공제를 먼저 하면) 총재직연수가 상한을 넘는
  사용자의 공제 효과가 왜곡된다 — 순서 오류를 잡아내는 회귀 테스트
  (`test_calculate_lump_sum_and_pension_applies_cap_before_deduction_not_after`)를
  추가했다.
- **영향 범위**: A(퇴직연금) baseline/Tier1 채점 경로(employees_service.py 기반)와는
  무관한 별도 엔드포인트(`/api/retirement/scenarios`)라 `defect_fix_comparison.md`의
  수치에는 영향이 없다 — 실측으로 확인함(표 B의 baseline BEFORE/AFTER가 완전히
  동일함).
- **테스트**: `tests/test_retirement_service.py`에 상한 초과 케이스, 순서 검증 케이스,
  기존 동작(상한 이내) 불변 케이스 3종 추가.
- **커밋**: `c6bc7aa` — 🐛 Fix: LUMP_SUM/SPLIT 재직기간 상한 누락 및 조기퇴직연금 감액
  소수 미달연수 대응 (§2와 동일 커밋)

---

## 2. [해결됨] 조기퇴직연금 감액 — 소수 미달연수 미대응 + 정합성 검증 부재

- **위치**: `fastapi/app/services/retirement_service.py`
  ```python
  EARLY_REDUCTION_RATE_PER_YEAR = 0.05
  ...
  ScenarioType.EARLY: (monthly_pension * (1 - EARLY_REDUCTION_RATE_PER_YEAR * early_years), asset)  # 수정 전
  ```
  `early_years`는 호출자가 직접 넘기는 정수(`EARLY_YEARS_MIN=1` ~ `EARLY_YEARS_MAX=5`).
- **[정정]** 최초 서술("계단식 로직 부재")은 부정확했다 — `early_years`가 정수일 때
  이 선형식은 법정 계단식 감액률(1년 이내 95%, 1년 초과~2년 이내 90%, 2년 초과~3년
  이내 85%, 3년 초과~4년 이내 80%, 4년 초과~5년 이내 75%)과 수치가 완전히 일치했다.
  실제 문제는 **소수 미달연수 미대응**이었다 — 예를 들어 1.5년 미달을 넣으면 계단이
  아니라 선형으로 처리돼(7.5% 감액) 법정 계단식(10% 감액, "1년 초과~2년 이내" 구간)
  보다 적게 감액됐다. 부수적으로 **미달연수 정합성 검증 부재**도 있었다 — 미달연수를
  지급개시연령으로부터 산정하는 로직이 엔진 밖(API 호출자)에 있어, 그 변환값이
  올바른지 엔진이 검증할 수 없었다.
- **조치**: `_early_reduction_rate(early_years)`가
  `EARLY_REDUCTION_RATE_PER_YEAR * ceil(early_years)`로 계단식을 명시적으로
  구현하도록 교체했다. `early_years` 필드 제약을 `ge=1`(정수)에서 `gt=0`(소수 허용,
  ≤5)으로 완화했다 — 필드 자체는 유지해 breaking change를 내지 않았다. 정수 입력 시
  `ceil(n) == n`이므로 결과가 이전 버전과 정확히 동일함을 회귀 테스트로 고정했다
  (`test_early_reduction_rate_matches_legacy_linear_formula_for_integer_input`,
  1~5 전수).
- **여전히 스코프 밖(TODO)**: 미달연수를 "법정 지급개시연령 - 실제 수령개시연령"으로
  서버가 직접 산정하는 기능은 포함하지 않았다 — 지급개시연령은 사학연금법령
  개정사항(2016.1.1, 퇴직연도별 60~65세 단계적 연장)에 따른 별도 표가 필요하다.
  코드에 TODO 주석, `scope_limitations.md` 향후 과제에 백로그 항목으로 기록했다.
  호출자가 `early_years`를 직접 산정해 넘겨야 하는 구조는 그대로다.
- **정량 검증**: 법정 지급개시연령 유예 스케줄을 확보하지 못해 여전히 보류.
  `phase5_qualitative.md`의 기술 통계(동일 재직연수구간x퇴직연도 내 30개 비교 셀 중
  27개에서 B의 평균 구간코드가 A보다 낮음)는 "조기수령이 정상보다 낮은 금액대에
  분포한다"는 방향성만 정성적으로 뒷받침하며, 5%/년 계단 폭 자체를 검증하지는 않는다.
  이 항목은 A(퇴직연금) baseline/Tier1 채점 경로(employees_service.py)와 무관해
  `defect_fix_comparison.md`의 수치에는 영향이 없다(실측 확인 완료).
- **테스트**: `tests/test_retirement_service.py`에 경계값(0/1/5/6년 포함), 계단 전환
  (1.0/1.5/4.9년), 회귀(정수 1~5) 테스트 추가.
- **커밋**: `c6bc7aa` — 🐛 Fix: LUMP_SUM/SPLIT 재직기간 상한 누락 및 조기퇴직연금 감액
  소수 미달연수 대응 (§1-1과 동일 커밋)

---

## 3. [관찰, 결함 아님] 공제일시금 공제연수 클램프

- **위치**: `fastapi/app/services/retirement_service.py::_resolve_split_deduction_years`
  ```python
  MIN_PENSION_YEARS = 10
  MAX_DEDUCTION_YEARS = 26
  max_allowed = min(total_service_years - MIN_PENSION_YEARS, MAX_DEDUCTION_YEARS)
  ```
- **관찰**: C(퇴직연금공제일시금) 표본(n=1,297)에서 `재직연수 - 10`의 최댓값은 23년으로,
  26년 상한은 이 데이터 범위 내에서 **한 건도 걸리지 않는다(0.00%)**. 결함으로
  단정할 근거는 없다 — 실제 선택된 공제연수가 데이터에 없어 클램프 기본값 자체의
  타당성은 검증 불가(`scope_limitations.md` 참조). 다만 이 population 범위 안에서는
  26년 클램프가 사실상 죽은 코드(dead branch)로 작동한다는 점만 기록한다.

---

## 4. [참고] Tier 1(법정 tranche 잠정 비교모형) vs baseline

`tier1_evaluation.md`의 tranche 분해 가능 표본(n=20,708, **A 전체(n=40,719)의 부분표본**
— 재직월수_상한도달여부==True 20,011행 제외 후)에서 baseline 전체 적중률 46.01% 대비
Tier 1은 35.00%로 오히려 낮다(닫힌 구간 기준 33.16% vs 19.43%). 이는
**"법정 요율이 틀렸다"는 뜻이 아니다** — 법정 요율은 전부 baseline의 단일 상수
(PENSION_RATE=1.7%)보다 높거나 같은데, baseline이 이미 미적중의 대부분
(**96.56%, n=20,708 tranche 부분표본 기준** — 위 1번 항목의 98.00%와는 표본이 달라
직접 비교 불가)을 과대추정하는 상태라 요율을 올리면 과대추정이 더 심화되는 것이
당연한 결과다. `tier1_evaluation.md`가 명시하듯, 이는 "보정률을 제외한 어떤 모형도
실지급액을 재현할 수 없다"는 것을 보여준다 — baseline이 Tier 1보다 덜 틀렸을 뿐, 0.017이
옳은 값이라거나 "위 1번 결함 수정만으로 정확도가 개선된다"는 뜻이 아니다.
보정률은 산식의 부수 요소가 아니라 필수 구성요소로 취급해야 한다.

민감도 분석(offset ±24개월)에서 Tier 1 적중률이 34.23%→35.90%로 단조 증가하는데,
이는 임용시점 추정이 정확했다는 근거가 **아니다** — offset을 늦출수록 pre-2010
구간(요율 2.0%) 비중이 줄어 예측 요율이 낮아지고, 이미 과대추정 중인 모형의
과대추정이 완화되는 구조적 현상이다(`tier1_evaluation.md` 민감도 분석 절 참조).

**[Step 4 실측으로 확인됨]** "위 1번 결함 수정만으로 정확도가 개선된다고 단정하지
말 것"이라는 위 예측은 실측으로 확인됐다 — 1번 결함을 실제로 고친 뒤
(`defect_fix_comparison.md`) baseline 적중률은 40,719행 중 3행만 바뀌어 사실상
불변이었다(43.54%→43.54%). 이 표본에서는 재직월수 자체가 이미 상한 근처에서
절단돼 있어 36년 캡이 걸릴 기회가 거의 없었기 때문이다.
