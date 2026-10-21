"""전체 재현: python run_all.py (data/raw 에 원자료 2개, data/adm 에 경계 파일이 있어야 함 — README 참고)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for step in ("01_prepare.py", "02_analysis.py", "03_figures_policy.py"):
    print(f"\n=== {step} ===", flush=True)
    subprocess.run([sys.executable, "-W", "ignore", str(ROOT / "src" / step)], check=True)
print("\n완료: outputs/tables, outputs/figures 확인")
