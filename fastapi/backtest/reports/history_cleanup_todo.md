# History Cleanup TODO — Phase 0에서 식별된 정리 대상

데이터 출처: 사학연금공단 제공 개인 단위 퇴직급여 마이크로데이터 (backtest/data/raw/).
취급 제한: 학교명 삭제, 금액은 구간값만 사용, 프로젝트 목적 외 사용·외부 노출 금지.

Phase 0(데이터 거버넌스 점검)에서 발견된 항목을 기록만 한다. `git filter-repo`,
`git rebase`, force push는 이 트랙에서 실행하지 않았다 — 팀과 조율 후 별도로 처리할 것.

## 1. [처리 필요] 현재 추적 중인 규칙 위반 파일

| 파일경로 | 문제 | 최초 커밋 |
|---|---|---|
| `fastapi/scripts/stats_output/retirement_pension_stats.csv` | `급여금액` 평균/중위값/p25/p75를 연령x직종x학교급으로 그룹화. count=1인 행이 다수라 그룹 평균이 사실상 개인 원본 지급액 그대로 노출됨 (규칙 2 위반) | `f8a06704dc2ef7a61757c3ce0163a5434548023a` |
| `fastapi/scripts/stats_output/severance_stats.csv` | 위와 동일 구조, 동일 문제 | `f8a06704dc2ef7a61757c3ce0163a5434548023a` |

**권장 조치(팀 조율 필요, 자동 실행 안 함)**: 두 파일을 구간 집계(count>=5 등 셀 억제 적용)로
재생성하거나, git 추적에서 제거하고 `.gitignore`에 추가. 이미 원격에 push된 상태이므로
단순 삭제로는 과거 커밋의 노출을 없앨 수 없다 — 히스토리에서 완전히 제거하려면
`git filter-repo` 등 히스토리 재작성이 필요하고, 이는 공유 저장소의 다른 클론을
깨뜨리므로 팀 합의 후 진행.

## 2. [저위험, 조치 불필요] active_income_stats.csv

`fastapi/data/active_income_stats.csv` — 구간별(총승인월수 버킷) 평균/중위값/p25/p75,
count 74,044~312,427로 대규모라 개인 재식별 위험 낮음. 이번 트랙의 사학연금 퇴직급여
데이터와는 다른 데이터셋(SRM189138)에서 파생됨. 조치 불필요, 참고로만 기록.

## 3. [로컬 전용, 낮은 우선순위] git stash 내 미추적 데이터

로컬 `refs/stash`(`stash@{0}`, 내부 커밋 `ed842ef01c4ceb1b5a6494c79f7cae93df1c1223`)에
아래 파일들이 남아있다. 어떤 브랜치에도 커밋된 적 없고 원격에 push되지 않아 팀원
클론에는 없다 — 로컬 저장소 소유자(개발자 본인) 판단에 맡긴다.

- `eda_output/*.png` 4개 (연도별/연령대별/직종별/학교급별 퇴직연금 수급액 그래프)
- `retirement_pension_stats_퇴직연금.csv`, `severance_stats_퇴직수당.csv`

필요 없으면 `git stash drop`으로 정리 가능(선택 사항, 자동 실행 안 함).

## 4. `.gitignore` 커버리지 — 개선 권고

`fastapi/backtest/data/`는 명시적 항목이 아니라 루트 `.gitignore`의 범용 `data/` 규칙에
얹혀 무시되는 상태다(`git check-ignore`로 검증 완료, 현재는 정상 동작). 향후 누군가
`data/` 규칙을 좁히면 조용히 뚫릴 수 있으므로, `backtest/data/`를 명시적 항목으로
추가하는 것을 권장한다(당장 위험은 아님, 낮은 우선순위).

## 5. 원본 파일 경로/파일명 불일치 (참고, 정리 대상 아님)

Phase 0 확인 당시 원본 파일의 실제 경로/파일명이 최초 지시문과 달랐다
(`fastapi/backtest/data/raw/2. (신정우 학생 양식)퇴직급여신청자 자료 추출_V1.xlsx`).
`build_clean_dataset.py`는 이 실제 경로를 기준으로 작성됐다. 히스토리 정리 대상은
아니며 참고용으로만 남긴다.
