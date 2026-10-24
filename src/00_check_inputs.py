"""00. 원자료 확인: 파일이 있는지, 분석에 쓴 파일과 같은지(행 수·핵심 합계·SHA-256) 점검.

다르면 경고만 내고 계속 진행합니다(포털 파일이 갱신되면 결과 숫자가 보고서와 달라질 수 있음).
종료 코드: 0 = 원자료 모두 있음, 2 = 원자료 없음(→ run_all.py --from-snapshot 사용)
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "bus_stops": (ROOT / "data/raw/bus_stops_20251031.csv",
                  "1db7e5d0cdc541e86a957b7584f2ddf8e4b1d29b02594984a01c5752ac13af06"),
    "population": (ROOT / "data/raw/pop_age_202609_v2.xlsx", None),  # 내려받을 때마다 파일 메타데이터가 바뀌어 해시 대신 합계로 확인
    "boundary": (ROOT / "data/adm/ver20261001/HangJeongDong_ver20261001.geojson",
                 "843ece3a0b3429742cd4a1b699cc13987a88b5e5401f382e7fdaaa194ea5e605"),
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


missing = [k for k, (p, _) in FILES.items() if not p.exists()]
if missing:
    print("원자료 없음:", ", ".join(missing))
    print("→ README의 '데이터' 절을 보고 내려받거나, python run_all.py --from-snapshot 으로 실행하세요.")
    sys.exit(2)

ok = True
for k, (p, ref) in FILES.items():
    if ref:
        got = sha256(p)
        same = got == ref
        ok &= same
        print(f"[{'OK' if same else '경고'}] {k}: SHA-256 {'일치' if same else '다름 — 포털 파일이 갱신됐을 수 있음'}")

s = pd.read_csv(FILES["bus_stops"][0], encoding="cp949", usecols=["도시명"])
print(f"[{'OK' if len(s) == 227065 else '경고'}] bus_stops: {len(s):,}행 (기준 227,065)")
raw = pd.read_excel(FILES["population"][0], header=None)
gg = raw[raw[0].astype(str).str.strip() == "4100000000"]
total = int(str(gg.iloc[0, 2]).replace(",", "")) if len(gg) else None
same = total == 13777186
ok &= same
print(f"[{'OK' if same else '경고'}] population: 경기도 총인구 {total:,}명 (기준 13,777,186, 2026년 9월 말)" if total else "[경고] population: 경기도 행을 찾지 못함 — '전체 읍면동' 연령별 인구현황 파일인지 확인")
print("입력 확인 완료" + ("" if ok else " (경고 있음: 결과가 보고서 숫자와 다를 수 있음)"))
