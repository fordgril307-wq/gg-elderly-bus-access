"""02. 분석: 고령 보행권 취약도 지수, 가중치 민감도, K-평균 유형화, 국지적 공간자기상관(LISA).

입력: data/processed/dong.gpkg (01 산출)
출력: data/processed/dong_scored.gpkg, outputs/tables/*.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import libpysal
from esda.moran import Moran, Moran_Local

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
SEED = 42
rng = np.random.default_rng(SEED)

d = gpd.read_file(PROC / "dong.gpkg")
d["density"] = d["pop_total"] / d["area_km2"]


def zs(x):
    return (x - x.mean()) / x.std()


def index_for(r, w=None):
    """취약도 지수: 접근 격차 2개 + 필요 2개, z점수 가중합(높을수록 취약)."""
    comp = pd.DataFrame({
        "gap_cov": zs(1 - d[f"cov{r}"]),                       # 보행권 밖 면적 비율
        "gap_dist": zs(np.log(d["dist_mean_m"])),             # 최근접 정류장 평균거리(로그)
        "need_share": zs(d["share_65"]),                      # 고령인구 비율
        "need_count": zs(np.log1p(d[f"uncov_65_{r}"])),       # 보행권 밖 추정 고령자 수(로그)
    })
    w = np.ones(4) / 4 if w is None else np.asarray(w)
    return comp, comp.values @ w


comp, d["vuln"] = index_for(300)
for k in comp:
    d[k] = comp[k].values
d["vuln_rank"] = d["vuln"].rank(ascending=False).astype(int)

# ---- 민감도 1: 보행권 반경 ----
sens = []
for r in (250, 400):
    _, v = index_for(r)
    rho = spearmanr(d["vuln"], v).correlation
    top_overlap = len(set(d.nlargest(60, "vuln").index) & set(pd.Series(v, index=d.index).nlargest(60).index)) / 60
    sens.append({"구분": f"반경 {r}m vs 300m", "스피어만 상관": round(rho, 3), "상위10%(60곳) 일치율": round(top_overlap, 3)})
# ---- 민감도 2: 가중치 무작위(디리클레) 1,000회 ----
top60 = set(d.nlargest(60, "vuln").index)
rhos, overlaps, in_top = [], [], np.zeros(len(d))
for _ in range(1000):
    w = rng.dirichlet(np.ones(4))
    v = comp.values @ w
    rhos.append(spearmanr(d["vuln"], v).correlation)
    top = np.argsort(-v)[:60]
    overlaps.append(len(top60 & set(d.index[top])) / 60)
    in_top[top] += 1
d["top10_freq"] = in_top / 1000
sens.append({"구분": "가중치 무작위 1,000회(중앙값)", "스피어만 상관": round(float(np.median(rhos)), 3),
             "상위10%(60곳) 일치율": round(float(np.median(overlaps)), 3)})
sens.append({"구분": "가중치 무작위 1,000회(하위 5%)", "스피어만 상관": round(float(np.percentile(rhos, 5)), 3),
             "상위10%(60곳) 일치율": round(float(np.percentile(overlaps, 5)), 3)})
pd.DataFrame(sens).to_csv(TAB / "sensitivity.csv", index=False, encoding="utf-8-sig")

# ---- K-평균 유형화 ----
feat_cols = ["log_density", "share_65", "cov300", "log_dist", "log_stops_1k65"]
X = pd.DataFrame({
    "log_density": np.log(d["density"]),
    "share_65": d["share_65"],
    "cov300": d["cov300"],
    "log_dist": np.log(d["dist_mean_m"]),
    "log_stops_1k65": np.log(d["stops_per_1k65"]),
})
Xs = StandardScaler().fit_transform(X)
sil = {}
for k in range(3, 8):
    lab = KMeans(k, n_init=20, random_state=SEED).fit_predict(Xs)
    sil[k] = silhouette_score(Xs, lab)
pd.Series(sil, name="silhouette").to_csv(TAB / "kmeans_silhouette.csv", encoding="utf-8-sig")
K = 4  # 해석 가능성과 실루엣을 함께 고려(표 참조) — 아래에서 실루엣 최댓값도 기록
best_k = max(sil, key=sil.get)
km = KMeans(K, n_init=50, random_state=SEED).fit(Xs)
d["cluster_raw"] = km.labels_
# 안정성: 부트스트랩 100회 재학습 후 원 군집과의 ARI
from sklearn.metrics import adjusted_rand_score
aris = []
for b in range(100):
    idx = rng.choice(len(Xs), len(Xs), replace=True)
    kb = KMeans(K, n_init=10, random_state=b).fit(Xs[idx])
    aris.append(adjusted_rand_score(km.labels_, kb.predict(Xs)))
prof = d.groupby("cluster_raw").agg(
    n=("adm_cd2", "size"), pop=("pop_total", "sum"), pop65=("pop_65", "sum"),
    density=("density", "median"), share_65=("share_65", "median"), cov300=("cov300", "median"),
    dist=("dist_mean_m", "median"), stops_1k65=("stops_per_1k65", "median"), vuln=("vuln", "mean"),
    eupmyeon_share=("eupmyeon", "mean"))
# 이름 붙이기: 취약도 평균 순
order = prof["vuln"].sort_values().index.tolist()
names = {order[0]: "A 도심 밀집형", order[1]: "B 도시 외곽형", order[2]: "C 도농 전이형", order[3]: "D 고령 분산형"}
d["cluster"] = d["cluster_raw"].map(names)
prof.index = prof.index.map(names)
prof = prof.sort_index()
prof.round(3).to_csv(TAB / "cluster_profile.csv", encoding="utf-8-sig")

# ---- 공간자기상관 ----
wq = libpysal.weights.Queen.from_dataframe(d, use_index=False, silence_warnings=True)
islands = wq.islands
wq.transform = "r"
np.random.seed(SEED); mi = Moran(d["vuln"].values, wq, permutations=999) if not islands else None
if islands:  # 섬(이웃 없는 폴리곤)이 있으면 KNN으로 대체
    wq = libpysal.weights.KNN.from_dataframe(d, k=6)
    wq.transform = "r"
    np.random.seed(SEED); mi = Moran(d["vuln"].values, wq, permutations=999)
lisa = Moran_Local(d["vuln"].values, wq, permutations=999, seed=SEED)
quad = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
d["lisa"] = [quad[q] if p < 0.05 else "ns" for q, p in zip(lisa.q, lisa.p_sim)]

# ---- 도시 속 사각지대: 동(洞) 중 보행권 밖 추정 고령자 상위 ----
urban = d[~d["eupmyeon"]].nlargest(15, "uncov_65_300")

summary = {
    "읍면동 수": len(d),
    "경기 고령인구(65+)": int(d["pop_65"].sum()),
    "고령인구 가중 평균 커버리지(300m)": round(float((d["cov300"] * d["pop_65"]).sum() / d["pop_65"].sum()), 3),
    "보행권(300m) 밖 추정 고령자 합계(상한)": int(d["uncov_65_300"].sum()),
    "읍면 평균 커버리지": round(float(d.loc[d.eupmyeon, "cov300"].mean()), 3),
    "동 평균 커버리지": round(float(d.loc[~d.eupmyeon, "cov300"].mean()), 3),
    "Moran's I": round(mi.I, 3), "Moran p": mi.p_sim,
    "LISA HH 수": int((d["lisa"] == "HH").sum()),
    "실루엣 최댓값 k": best_k, "채택 k": K, "k=4 실루엣": round(sil[4], 3),
    "군집 부트스트랩 ARI 중앙값": round(float(np.median(aris)), 3),
    "군집 부트스트랩 ARI 하위5%": round(float(np.percentile(aris, 5)), 3),
}
pd.Series(summary).to_csv(TAB / "summary.csv", header=["값"], encoding="utf-8-sig")
cols = ["vuln_rank", "adm_nm", "cluster", "lisa", "pop_total", "pop_65", "share_65", "n_stops",
        "cov300", "dist_mean_m", "uncov_65_300", "top10_freq", "vuln"]
d.sort_values("vuln", ascending=False)[cols].to_csv(TAB / "vulnerability_rank.csv", index=False, encoding="utf-8-sig")
urban[cols].to_csv(TAB / "urban_blindspots.csv", index=False, encoding="utf-8-sig")
d.to_file(PROC / "dong_scored.gpkg", driver="GPKG")

for k, v in summary.items():
    print(f"{k}: {v}")
print(pd.DataFrame(sens).to_string())
print(pd.Series(sil).round(3).to_string())
print(prof.round(3).to_string())
print(d.sort_values("vuln", ascending=False)[cols].head(20).round(3).to_string())
print(urban[cols].round(3).to_string())
