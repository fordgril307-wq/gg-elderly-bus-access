"""04. 결선 발표용 지도(범례를 오른쪽에 둔 가로형) — outputs/figures/slide_map_*.png"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures"
for name in ("Pretendard", "Noto Sans CJK KR", "NanumGothic", "Malgun Gothic"):
    if any(name == f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({"figure.dpi": 300, "axes.unicode_minus": False})
INK = "#222222"
d = gpd.read_file(ROOT / "data/processed/dong_scored.gpkg")
si = d.assign(si=d["adm_nm"].str.split(" ").str[1].str.replace(r"(시|군).*", r"\1", regex=True)).dissolve("si")


def frame(legend, fname, colors):
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    d.plot(color=colors, ax=ax, linewidth=0.05, edgecolor="#ffffff")
    si.boundary.plot(ax=ax, color="#ffffff", linewidth=0.7)
    ax.set_axis_off()
    ax.legend(handles=legend, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8.5,
              labelcolor=INK, handlelength=1.4, handleheight=1.1)
    fig.subplots_adjust(left=0, right=0.66, top=1, bottom=0)
    fig.savefig(FIG / fname, facecolor="white")
    plt.close(fig)


BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#104281"]
q = pd.qcut(d["vuln"], 6, labels=False)
frame([Patch(color=BLUE[0], label="취약도 낮음")] + [Patch(color=c, label=" ") for c in BLUE[1:-1]] + [Patch(color=BLUE[-1], label="취약도 높음")],
      "slide_map_index.png", q.map(dict(enumerate(BLUE))))
col = {"HH": "#eb6834", "LL": "#2a78d6", "HL": "#f3b48f", "LH": "#f3b48f", "ns": "#e6e5e1"}
n = d["lisa"].value_counts()
frame([Patch(color=col["HH"], label=f"취약-취약 군집 {n.get('HH', 0)}곳"),
       Patch(color=col["LL"], label=f"양호-양호 군집 {n.get('LL', 0)}곳"),
       Patch(color=col["HL"], label=f"섬형 이상치 {n.get('HL', 0) + n.get('LH', 0)}곳"),
       Patch(color=col["ns"], label="유의하지 않음")],
      "slide_map_lisa.png", d["lisa"].map(col))
print("ok")
