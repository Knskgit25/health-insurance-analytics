"""
Cross-platform task runner mirroring Makefile targets for Windows, macOS, and Linux.
Usage:
    python make.py [target]
    e.g. python make.py all
"""

import sys
import subprocess
import shutil
import glob
from pathlib import Path


def run_cmd(cmd: list[str] | str, check: bool = True) -> int:
    print(f"\n>>> Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    ret = subprocess.run(cmd, shell=isinstance(cmd, str))
    if check and ret.returncode != 0:
        print(f"Error: command failed with return code {ret.returncode}")
        sys.exit(ret.returncode)
    return ret.returncode


def target_setup():
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def target_data():
    run_cmd([sys.executable, "src/data_generation/run_generation.py"])


def target_warehouse():
    run_cmd([sys.executable, "src/warehouse/build_warehouse.py"])
    run_cmd([sys.executable, "src/warehouse/data_quality.py"])


def target_kpis():
    run_cmd([sys.executable, "src/analysis/kpis.py"])


def target_eda():
    run_cmd([sys.executable, "src/analysis/eda.py"])


def target_models():
    run_cmd([sys.executable, "src/ml/evaluate.py"])


def target_dashboard():
    run_cmd([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"])


def target_test():
    run_cmd([sys.executable, "-m", "ruff", "check", "src/", "tests/"])
    run_cmd([sys.executable, "-m", "pytest", "tests/"])


def target_all():
    print("\n" + "=" * 60)
    print("EXECUTING FULL PIPELINE: data -> warehouse -> kpis -> eda -> models -> test")
    print("=" * 60)
    target_data()
    target_warehouse()
    target_kpis()
    target_eda()
    target_models()
    target_test()
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE - ALL TARGETS SUCCEEDED!")
    print("=" * 60)


def target_clean():
    dirs = ["data/raw", "data/processed", "data/warehouse", "models", "reports/figures", ".pytest_cache", ".ruff_cache"]
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
        print(f"Removed {d}")
    for f in glob.glob("*.log"):
        try:
            Path(f).unlink()
        except OSError:
            pass
    print("Clean completed.")


TARGETS = {
    "setup": target_setup,
    "data": target_data,
    "warehouse": target_warehouse,
    "kpis": target_kpis,
    "eda": target_eda,
    "models": target_models,
    "dashboard": target_dashboard,
    "test": target_test,
    "all": target_all,
    "clean": target_clean,
}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "help"
    if target in ["help", "-h", "--help"]:
        print("Available targets:")
        for t in TARGETS:
            print(f"  python make.py {t}")
        return
    if target not in TARGETS:
        print(f"Unknown target '{target}'. Available: {list(TARGETS.keys())}")
        sys.exit(1)
    TARGETS[target]()


if __name__ == "__main__":
    main()

