.PHONY: setup data warehouse kpis eda models dashboard test all clean help

PYTHON ?= python

help:
	@echo "Available commands:"
	@echo "  make setup      - Install dependencies from requirements.txt"
	@echo "  make data       - Generate synthetic raw insurance datasets"
	@echo "  make warehouse  - Clean data, build DuckDB warehouse, validate schema"
	@echo "  make kpis       - Execute KPI SQL analytics and export summaries"
	@echo "  make eda        - Run exploratory analysis and generate figures"
	@echo "  make models     - Train, evaluate, and serialize ML models"
	@echo "  make dashboard  - Launch interactive Streamlit analytics dashboard"
	@echo "  make test       - Run test suite and style checks"
	@echo "  make all        - Full pipeline: data -> warehouse -> kpis -> eda -> models -> test"
	@echo "  make clean      - Remove generated data, duckdb, and artifacts"

setup:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) src/data_generation/run_generation.py

warehouse:
	$(PYTHON) src/warehouse/build_warehouse.py
	$(PYTHON) src/warehouse/data_quality.py

kpis:
	$(PYTHON) src/analysis/kpis.py

eda:
	$(PYTHON) src/analysis/eda.py

models:
	$(PYTHON) src/ml/evaluate.py

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

test:
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m pytest tests/

all: data warehouse kpis eda models test

clean:
	$(PYTHON) -c "import shutil, os, glob; [shutil.rmtree(p, ignore_errors=True) for p in ['data/raw', 'data/processed', 'data/warehouse', 'models', 'reports/figures', '.pytest_cache', '.ruff_cache']]; [os.remove(f) for f in glob.glob('*.log')]"

