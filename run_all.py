"""전체 재현.

    python run_all.py                  # 원자료(data/raw, data/adm)로 처음부터 (약 1분)
    python run_all.py --from-snapshot  # 원자료 없이, 저장소에 포함된 가공 데이터(data/snapshot)로 02단계부터 (약 15초)
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot" / "dong.gpkg"
PROC = ROOT / "data" / "processed"


def run(step):
    print(f"\n=== {step} ===", flush=True)
    subprocess.run([sys.executable, "-W", "ignore", str(ROOT / "src" / step)], check=True)


t0 = time.time()
if "--from-snapshot" in sys.argv:
    PROC.mkdir(parents=True, exist_ok=True)
    shutil.copy(SNAP, PROC / "dong.gpkg")
    (ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    print("가공 데이터 스냅숏 사용: data/snapshot/dong.gpkg → data/processed/dong.gpkg (01단계 생략)")
    steps = ["02_analysis.py", "03_figures_policy.py", "04_slide_maps.py"]
else:
    chk = subprocess.run([sys.executable, str(ROOT / "src" / "00_check_inputs.py")])
    if chk.returncode == 2:
        sys.exit("원자료가 없습니다. README '데이터' 절을 보거나 python run_all.py --from-snapshot 으로 실행하세요.")
    steps = ["01_prepare.py", "02_analysis.py", "03_figures_policy.py", "04_slide_maps.py"]
for s in steps:
    run(s)
print(f"\n완료 ({time.time() - t0:.0f}초): outputs/tables, outputs/figures 확인")
