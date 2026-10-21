"""01. 데이터 준비: 경기도 읍면동 경계 + 연령별 인구 + 버스정류장 결합, 보행권 지표 산출.

입력
- data/raw/pop_age_202609_v2.xlsx : 행정안전부 주민등록 연령별 인구현황(2026년 9월 말, 읍면동, 5세 단위)
- data/raw/bus_stops_20251031.csv : 국토교통부 전국 버스정류장 위치정보(정보수집일 2025-10-31)
- data/adm/ver20261001/HangJeongDong_ver20261001.geojson : vuski/admdongkor 행정동 경계(2026-10-01)
출력
- data/processed/dong.gpkg, data/processed/dong.csv, outputs/tables/prep_log.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
PROC.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

CRS = 5179            # UTM-K (m 단위)
RADII = [250, 300, 400]
log = []

# ---------- 1. 인구 ----------
raw = pd.read_excel(RAW / "pop_age_202609_v2.xlsx", header=None)
hdr = raw.iloc[3].tolist()
body = raw.iloc[4:].copy()
# 앞쪽 '계' 블록(총 인구수 ~ 100세 이상)만 사용
total_cols = hdr[: hdr.index("남 인구수")]
body = body.iloc[:, : len(total_cols)]
body.columns = total_cols
body["행정기관코드"] = body["행정기관코드"].astype(str).str.strip()
for c in total_cols[2:]:
    body[c] = pd.to_numeric(body[c].astype(str).str.replace(",", ""), errors="coerce")

elder_cols = ["65~69세", "70~74세", "75~79세", "80~84세", "85~89세", "90~94세", "95~99세", "100세 이상"]
old75_cols = elder_cols[2:]
pop = pd.DataFrame({
    "adm_cd2": body["행정기관코드"],
    "pop_name": body["행정기관"].astype(str).str.strip(),
    "pop_total": body["총 인구수"],
    "pop_65": body[elder_cols].sum(axis=1),
    "pop_75": body[old75_cols].sum(axis=1),
})
# 읍면동 행만(코드 끝 2자리 00이 아니고 하위 5자리가 00000이 아닌 것)
pop = pop[pop["adm_cd2"].str.startswith("41") & (pop["adm_cd2"].str[-5:] != "00000")]
pop = pop[pop["adm_cd2"].str[5:8] != "000"]
# 남양주시 화도읍 동부·남부출장소는 주민등록 통계에만 따로 집계되고 경계는 화도읍 하나 → 화도읍에 합산
pop["adm_cd2"] = pop["adm_cd2"].replace({"4136025700": "4136025600", "4136025800": "4136025600"})
pop = pop.groupby("adm_cd2", as_index=False).agg(
    pop_name=("pop_name", "first"), pop_total=("pop_total", "sum"),
    pop_65=("pop_65", "sum"), pop_75=("pop_75", "sum"))
gyeonggi_total = body.loc[body["행정기관코드"] == "4100000000", "총 인구수"].iloc[0]
log.append(("인구: 경기도 총인구(시도 행)", int(gyeonggi_total)))
log.append(("인구: 경기도 읍면동 행 수", len(pop)))
log.append(("인구: 읍면동 합계", int(pop["pop_total"].sum())))

# ---------- 2. 경계 ----------
g = gpd.read_file(ROOT / "data/adm/ver20261001/HangJeongDong_ver20261001.geojson")
g = g[g["sidonm"] == "경기도"].copy()
g["adm_cd2"] = g["adm_cd2"].astype(str)
g = g.to_crs(CRS)
log.append(("경계: 경기도 읍면동 폴리곤 수", len(g)))

d = g.merge(pop, on="adm_cd2", how="left", indicator=True)
unmatched_geo = d[d["_merge"] == "left_only"]["adm_nm"].tolist()
unmatched_pop = sorted(set(pop["adm_cd2"]) - set(g["adm_cd2"]))
log.append(("결합: 경계에만 있고 인구 없음", len(unmatched_geo)))
log.append(("결합: 인구에만 있고 경계 없음", len(unmatched_pop)))
pd.Series(unmatched_geo, name="adm_nm").to_csv(TAB / "unmatched_boundary.csv", index=False)
pop[pop["adm_cd2"].isin(unmatched_pop)].to_csv(TAB / "unmatched_population.csv", index=False)
d = d[d["_merge"] == "both"].drop(columns="_merge")
d["sgg_name"] = d["adm_nm"].str.split(" ").str[1]
d["area_km2"] = d.geometry.area / 1e6
d["eupmyeon"] = d["adm_nm"].str.endswith(("읍", "면"))
log.append(("분석 대상 읍면동 수", len(d)))
log.append(("분석 대상 인구 합계", int(d["pop_total"].sum())))

# ---------- 3. 정류장 ----------
s = pd.read_csv(RAW / "bus_stops_20251031.csv", encoding="cp949", dtype={"정류장번호": str})
log.append(("정류장: 전국 원자료 행 수", len(s)))
s = s.dropna(subset=["위도", "경도"])
s = s[(s["위도"].between(33, 39)) & (s["경도"].between(124, 132))]
sg = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s["경도"], s["위도"]), crs=4326).to_crs(CRS)
# 경기도 경계 10km 이내(서울·인천·충청 경계 정류장도 경기 주민이 이용 가능하므로 포함)
gy_union = d.union_all()
sg = sg[sg.intersects(gy_union.buffer(10_000))]
log.append(("정류장: 경기 및 인접 10km 행 수", len(sg)))
# 같은 위치(10m 격자) 중복 제거 — BIS 중복 등록·양방향 동일 지점
sg["gx"] = (sg.geometry.x // 10).astype(int)
sg["gy"] = (sg.geometry.y // 10).astype(int)
sg = sg.drop_duplicates(["gx", "gy"])
log.append(("정류장: 10m 중복 제거 후", len(sg)))
sg[["정류장번호", "정류장명", "도시명", "geometry"]].to_file(PROC / "stops.gpkg", driver="GPKG")

# 읍면동 안 정류장 수
inside = gpd.sjoin(sg[["geometry"]], d[["adm_cd2", "geometry"]], predicate="within", how="inner")
cnt = inside.groupby("adm_cd2").size()
d["n_stops"] = d["adm_cd2"].map(cnt).fillna(0).astype(int)
log.append(("정류장: 경기 읍면동 내부 정류장 수", int(d["n_stops"].sum())))

# ---------- 4. 보행권 커버리지(면적 기준) ----------
for r in RADII:
    buf = gpd.GeoSeries(sg.buffer(r, resolution=8), crs=CRS).union_all()
    cov = d.geometry.intersection(buf).area
    d[f"cov{r}"] = (cov / d.geometry.area).clip(0, 1)

# 최근접 정류장까지 평균 거리: 읍면동 내 100m 격자점 기준
from shapely import points
from scipy.spatial import cKDTree
tree = cKDTree(np.c_[sg.geometry.x, sg.geometry.y])
mean_d, p90_d = [], []
for geom in d.geometry:
    minx, miny, maxx, maxy = geom.bounds
    step = 100 if geom.area < 2e7 else 200
    xs, ys = np.meshgrid(np.arange(minx, maxx, step), np.arange(miny, maxy, step))
    pts = points(xs.ravel(), ys.ravel())
    m = gpd.GeoSeries(pts).within(geom).values
    if m.sum() == 0:
        c = geom.representative_point()
        xy = np.array([[c.x, c.y]])
    else:
        xy = np.c_[xs.ravel()[m], ys.ravel()[m]]
    dist, _ = tree.query(xy)
    mean_d.append(dist.mean()); p90_d.append(np.percentile(dist, 90))
d["dist_mean_m"] = mean_d
d["dist_p90_m"] = p90_d

d["share_65"] = d["pop_65"] / d["pop_total"]
d["stops_per_1k65"] = d["n_stops"] / d["pop_65"].replace(0, np.nan) * 1000
# 보행권 밖 고령자 추정(면적 균등 분포 가정 — 상한 추정치, 보고서에 한계 명시)
for r in RADII:
    d[f"uncov_65_{r}"] = d["pop_65"] * (1 - d[f"cov{r}"])

d.to_file(PROC / "dong.gpkg", driver="GPKG")
d.drop(columns="geometry").to_csv(PROC / "dong.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(log, columns=["항목", "값"]).to_csv(TAB / "prep_log.csv", index=False, encoding="utf-8-sig")
for k, v in log:
    print(f"{k}: {v}")
print(d[["pop_total", "pop_65", "share_65", "n_stops", "cov300", "dist_mean_m", "stops_per_1k65"]].describe().round(3).to_string())
