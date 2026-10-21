"""03. 그림·정책 표·탄소 손익분기 시나리오.

입력: data/processed/dong_scored.gpkg
출력: outputs/figures/fig1~fig4.png, outputs/tables/priority_*.csv, carbon_breakeven.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap, BoundaryNorm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# ---- 폰트 ----
for name in ("Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic"):
    if any(name in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e",
                     "xtick.color": "#52514e", "ytick.color": "#52514e", "figure.dpi": 300})
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#104281"]
CAT = {"A 도심 밀집형": "#c9c8c2", "B 도시 외곽형": "#2a78d6", "C 도농 전이형": "#1baf7a", "D 고령 분산형": "#eb6834"}
W = 14 / 2.54

d = gpd.read_file(PROC / "dong_scored.gpkg")
sgg = d.dissolve("sgg_name") if "sgg_name" in d else None
outline = d.assign(si=d["adm_nm"].str.split(" ").str[1].str.replace(r"(시|군).*", r"\1", regex=True)).dissolve("si")


def base(ax):
    outline.boundary.plot(ax=ax, color="#ffffff", linewidth=0.6)
    ax.set_axis_off()


# ---- 그림 1: 취약도 지수 지도 + LISA ----
fig, axes = plt.subplots(1, 2, figsize=(W, W * 0.62))
q = pd.qcut(d["vuln"], 6, labels=False)
cmap = ListedColormap(BLUE)
d.assign(q=q).plot(column="q", cmap=cmap, ax=axes[0], linewidth=0.05, edgecolor="#ffffff")
base(axes[0])
axes[0].set_title("(a) 고령 보행권 취약도 지수(6분위)", fontsize=8, color=INK, loc="left")
axes[0].legend(handles=[Patch(color=BLUE[0], label="낮음"), Patch(color=BLUE[-1], label="높음")],
               loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=7)
lisa_col = {"HH": "#eb6834", "LL": "#2a78d6", "HL": "#f3b48f", "LH": "#9ec5f4", "ns": "#ecebe7"}
d.plot(color=d["lisa"].map(lisa_col).where(~d["lisa"].isin(["LH"]), lisa_col["HL"]), ax=axes[1], linewidth=0.05, edgecolor="#ffffff")
base(axes[1])
axes[1].set_title("(b) 취약 집중지역(LISA, p<0.05)", fontsize=8, color=INK, loc="left")
axes[1].legend(handles=[Patch(color=lisa_col["HH"], label=f"취약-취약 군집 {int((d.lisa=='HH').sum())}곳"),
                        Patch(color=lisa_col["LL"], label=f"양호-양호 군집 {int((d.lisa=='LL').sum())}곳"),
                        Patch(color=lisa_col["HL"], label="섬형 이상치(HL·LH)"),
                        Patch(color=lisa_col["ns"], label="유의하지 않음")],
               loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=6.5)
fig.tight_layout()
fig.savefig(FIG / "fig1_vuln_lisa.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---- 그림 2: 유형 지도 + '정류장 수의 착시' ----
prof = pd.read_csv(TAB / "cluster_profile.csv", index_col=0)
fig = plt.figure(figsize=(W, W * 0.55))
ax0 = fig.add_axes([0.0, 0.12, 0.42, 0.8])
d.plot(color=d["cluster"].map(CAT), ax=ax0, linewidth=0.05, edgecolor="#ffffff")
base(ax0)
ax0.set_title("(a) 읍면동 유형(K-평균, k=4)", fontsize=8, color=INK, loc="left")
ax0.legend(handles=[Patch(color=c, label=f"{k} ({int(prof.loc[k, 'n'])})") for k, c in CAT.items()],
           loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=False, fontsize=6.5)
ax1 = fig.add_axes([0.52, 0.16, 0.2, 0.68])
ax2 = fig.add_axes([0.79, 0.16, 0.2, 0.68])
labs = [k.split(" ")[0] for k in prof.index]
cols = [CAT[k] for k in prof.index]
ax1.bar(labs, prof["stops_1k65"], color=cols, width=0.6)
ax1.set_title("(b) 고령자 1천 명당\n정류장 수(중앙값)", fontsize=7.5, color=INK, loc="left")
for i, v in enumerate(prof["stops_1k65"]):
    ax1.text(i, v + 1, f"{v:.0f}", ha="center", fontsize=7, color=INK2)
ax2.bar(labs, prof["cov300"] * 100, color=cols, width=0.6)
ax2.set_title("(c) 300m 보행권\n면적 비율(%, 중앙값)", fontsize=7.5, color=INK, loc="left")
for i, v in enumerate(prof["cov300"] * 100):
    ax2.text(i, v + 2, f"{v:.0f}", ha="center", fontsize=7, color=INK2)
for a in (ax1, ax2):
    a.yaxis.grid(True, color=GRID, linewidth=0.5); a.set_axisbelow(True)
    a.tick_params(length=0)
ax2.set_ylim(0, 110)
fig.savefig(FIG / "fig2_cluster_paradox.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---- 우선순위 표 ----
cols_out = ["vuln_rank", "adm_nm", "cluster", "lisa", "pop_65", "share_65", "n_stops", "cov300",
            "dist_mean_m", "uncov_65_300", "top10_freq"]
pri = d[(d["lisa"] == "HH") & (d["top10_freq"] >= 0.5)].sort_values("vuln", ascending=False)
pri[cols_out].to_csv(TAB / "priority_drt.csv", index=False, encoding="utf-8-sig")
pri_sgg = pri.assign(si=pri["adm_nm"].str.split(" ").str[1]).groupby("si").agg(
    n=("adm_cd2", "size"), pop65=("pop_65", "sum"), uncov65=("uncov_65_300", "sum")).sort_values("uncov65", ascending=False)
pri_sgg.round(0).to_csv(TAB / "priority_drt_by_sgg.csv", encoding="utf-8-sig")

# ---- 그림 3: 우선 투입 후보 상위 20 ----
top = pri.head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(W, W * 0.62))
names = top["adm_nm"].str.replace("경기도 ", "")
ax.barh(names, top["uncov_65_300"], color="#eb6834", height=0.62)
for y, (v, c) in enumerate(zip(top["uncov_65_300"], top["dist_mean_m"])):
    ax.text(v + 30, y, f"{v:,.0f}명 · 평균 {c/1000:.1f}km", va="center", fontsize=6.5, color=INK2)
ax.set_xlabel("300m 보행권 밖 추정 고령자 수(명, 상한 추정)")
ax.xaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0, labelsize=7)
ax.set_xlim(0, top["uncov_65_300"].max() * 1.45)
fig.tight_layout()
fig.savefig(FIG / "fig3_priority.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---- 탄소 손익분기 시나리오 (모든 값은 가정, 보고서 표에 명시) ----
P = {
    "car_kg_km": 0.17,          # 승용차 1대 주행 1km당 CO2(가정 기준값, 범위 0.12~0.20)
    "pickup_factor": 2.0,       # 가족 픽업: 데려다주고 빈 차로 돌아오는 왕복 → 1인 이동당 주행거리 2배
    "detour": 1.3,              # DRT 우회·공차 계수(가정)
    "diesel_van_kg_km": 0.27,   # 경유 승합(11~15인승) 1km당 CO2(가정)
    "ev_kwh_km": 0.22,          # 전기 승합 전비(kWh/km, 가정)
    "grid_kg_kwh": 0.45,        # 전력 배출계수(kg/kWh, 가정)
}
ev_kg_km = P["ev_kwh_km"] * P["grid_kg_kwh"]
occ = np.arange(1, 8.01, 0.25)
rows = []
for o in occ:
    rows.append({"평균 동승 인원": o,
                 "경유 DRT 1인당": P["diesel_van_kg_km"] * P["detour"] / o,
                 "전기 DRT 1인당": ev_kg_km * P["detour"] / o})
cb = pd.DataFrame(rows)
car_self = P["car_kg_km"]
car_pick = P["car_kg_km"] * P["pickup_factor"]
cb["자가용(본인 운전)"] = car_self
cb["가족 픽업(왕복)"] = car_pick
cb.round(4).to_csv(TAB / "carbon_breakeven.csv", index=False, encoding="utf-8-sig")
be = {
    "경유DRT_vs_본인운전": P["diesel_van_kg_km"] * P["detour"] / car_self,
    "경유DRT_vs_가족픽업": P["diesel_van_kg_km"] * P["detour"] / car_pick,
    "전기DRT_vs_본인운전": ev_kg_km * P["detour"] / car_self,
    "전기DRT_vs_가족픽업": ev_kg_km * P["detour"] / car_pick,
}
# 승용차 배출계수 범위에 따른 손익분기 범위
for lo_hi, c in (("low", 0.12), ("high", 0.20)):
    be[f"경유DRT_vs_본인운전_car{c}"] = P["diesel_van_kg_km"] * P["detour"] / c
    be[f"전기DRT_vs_본인운전_car{c}"] = ev_kg_km * P["detour"] / c
pd.Series(be).round(2).to_csv(TAB / "carbon_breakeven_points.csv", header=["손익분기 동승 인원(명)"], encoding="utf-8-sig")
pd.Series(P).to_csv(TAB / "carbon_assumptions.csv", header=["값"], encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(W, W * 0.45))
ax.plot(cb["평균 동승 인원"], cb["경유 DRT 1인당"] * 1000, color="#6250d6", lw=2, label="경유 DRT")
ax.plot(cb["평균 동승 인원"], cb["전기 DRT 1인당"] * 1000, color="#1baf7a", lw=2, label="전기 DRT")
ax.axhline(car_self * 1000, color=INK2, lw=1, ls="--")
ax.axhline(car_pick * 1000, color=INK2, lw=1, ls=":")
ax.text(8.05, car_self * 1000, "자가용 본인 운전", va="center", fontsize=6.5, color=INK2)
ax.text(8.05, car_pick * 1000, "가족 픽업(왕복)", va="center", fontsize=6.5, color=INK2)
ax.text(6.0, P["diesel_van_kg_km"] * P["detour"] / 6.0 * 1000 + 14, "경유 DRT", fontsize=7, color="#6250d6")
ax.text(6.0, ev_kg_km * P["detour"] / 6.0 * 1000 + 10, "전기 DRT", fontsize=7, color="#1baf7a")
ax.set_xlabel("DRT 1회 운행 평균 동승 인원(명)")
ax.set_ylabel("이동 1인·1km당 CO2(g)")
ax.set_xlim(1, 8); ax.set_ylim(0, 380)
ax.yaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIG / "fig4_carbon_breakeven.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

print(pri_sgg.round(0).to_string())
print("후보 수", len(pri), "고령자", int(pri.pop_65.sum()), "보행권 밖", int(pri.uncov_65_300.sum()))
print(pd.Series(be).round(2).to_string())
