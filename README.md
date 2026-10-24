# 정류장은 많은데 걸어갈 수 없다
경기도 602개 읍면동의 고령 보행권 사각지대 탐지와 전기 수요응답버스 우선 투입 제안

한겨레 × 재단법인 숲과나눔 「AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」(2026) 출품작(김혜수)의 분석 코드·표·그림입니다.

보고서: [report/김혜수_분석보고서.pdf](report/김혜수_분석보고서.pdf)

## 실행
```bash
pip install -r requirements.txt       # Python 3.11~3.13에서 확인
python run_all.py --from-snapshot     # 원자료 없이 바로 실행 (약 15초)
python run_all.py                     # 원자료로 처음부터 (약 1분, 아래 '데이터' 절의 파일 필요)
```
- `--from-snapshot`: 저장소에 포함된 가공 데이터 `data/snapshot/dong.gpkg`(01단계 결과, 602개 읍면동)로 02~04단계를 실행합니다. 심사·검증용으로 원자료 없이 모든 표·그림이 다시 만들어집니다.
- 원자료 실행은 먼저 `src/00_check_inputs.py`가 파일 유무, SHA-256, 행 수, 경기도 총인구(13,777,186명)를 확인합니다.

| 단계 | 파일 | 하는 일 |
|---|---|---|
| 00 | `src/00_check_inputs.py` | 원자료가 분석에 쓴 파일과 같은지 확인 |
| 01 | `src/01_prepare.py` | 인구·경계·정류장 결합, 300/250/400m 보행권 면적 비율, 최근접 정류장 평균거리 |
| 02 | `src/02_analysis.py` | 취약도 지수, 반경·가중치 민감도(1,000회), K-평균(k=4)·부트스트랩 ARI, Moran's I·LISA |
| 03 | `src/03_figures_policy.py` | 그림 1~4, DRT 우선 투입 후보표, 탄소 손익분기 시나리오 |
| 04 | `src/04_slide_maps.py` | 결선 발표용 지도(취약도 6분위, LISA) |

난수 시드 42로 고정되어 같은 입력이면 같은 결과가 나옵니다(원자료로 다시 실행한 표·그림이 제출본과 바이트 단위로 같음을 확인). 그림의 한글 글꼴은 Pretendard·Noto Sans CJK KR·나눔고딕·맑은 고딕 중 설치된 것을 씁니다.

## 데이터 (저장소에 원자료 미포함 — 아래에서 직접 내려받아 같은 이름으로 저장)
| 데이터 | 제공 | 기준시점 | 저장 위치 | 이용조건 |
|---|---|---|---|---|
| 국토교통부_전국 버스정류장 위치정보 (https://www.data.go.kr/data/15067528/fileData.do) | 국토교통부 / 공공데이터포털 | 2025-10-31 | `data/raw/bus_stops_20251031.csv` (CP949) | 이용허락범위 제한 없음 |
| 주민등록 연령별 인구현황 (https://jumin.mois.go.kr → 연령별 인구현황, 월간 2026년 9월, 5세 단위, 0~100세 이상, 전국 읍면동) | 행정안전부 | 2026-09-30 | `data/raw/pop_age_202609_v2.xlsx` | 공개 통계 |
| 행정동 경계 HangJeongDong_ver20261001.geojson (https://github.com/vuski/admdongkor) | 통계청 SGIS, 가공 vuski/admdongkor | 2026-10-01 | `data/adm/ver20261001/` | 공공누리 제1유형, CC BY 4.0 |

경계 출처 표기: 본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor, https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다.

## 결과물
- `outputs/tables/` : `summary.csv`, `sensitivity.csv`, `cluster_profile.csv`, `vulnerability_rank.csv`(602곳 전체 순위), `priority_drt.csv`(DRT 우선 투입 56곳), `priority_drt_by_sgg.csv`, `urban_blindspots.csv`, `carbon_*.csv`, `prep_log.csv`(전처리 건수 기록)
- `outputs/figures/` : 보고서 그림 1~4, 발표용 지도 2개 (PNG, 300dpi)

## 한계
- 배차 간격·운행 횟수 미반영, 거리는 직선거리.
- 보행권 밖 고령자는 읍면동 안 인구 균등 분포를 가정한 상한 추정치(산지가 넓은 곳은 과대 가능).
- 탄소 계산은 공개 가정값에 따른 손익분기 시나리오(`src/03_figures_policy.py`의 가정값 `P`를 바꾸면 재계산, 사용값은 `carbon_assumptions.csv`).

## AI 사용
Claude(Anthropic, Claude Opus 5.5)로 코드 작성·실행, 그림 제작, 보고서 초안 작성을 했습니다. AI는 데이터 값을 만들거나 보완하지 않았고, 모든 수치는 위 코드의 산출물입니다. 입력한 자료는 공개 데이터와 그 집계, 코드뿐입니다. 결과 재현에 AI 서비스·유료 소프트웨어·API 키는 필요 없습니다. 자세한 내용은 `docs/ai_log.md`.
