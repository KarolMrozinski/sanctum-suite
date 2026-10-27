.PHONY: help install test clean status run-cycle override-on override-off

help:
	@echo "=== SANCTUM SUITE: AUTOMATION & MANAGEMENT ==="
	@echo "  make install      - Instalacja pakietu w trybie deweloperskim"
	@echo "  make test         - Uruchomienie wszystkich testów jednostkowych i integracyjnych"
	@echo "  make status       - Sprawdzenie statusu systemu i agentów przez CLI"
	@echo "  make run-cycle    - Ręczne wyzwolenie autonomicznego cyklu agentów"
	@echo "  make override-on  - Włączenie blokady nadzoru operatora (Operator Override)"
	@echo "  make override-off - Wyłączenie blokady (Tryb w pełni autonomiczny)"
	@echo "  make clean        - Czyszczenie plików tymczasowych i cache Pythona"

install:
	pip install --upgrade pip
	pip install -e .

test:
	pytest -v

status:
	python3 -m sanctum_suite.cli status

run-cycle:
	python3 -m sanctum_suite.cli run-cycle

override-on:
	python3 -m sanctum_suite.cli override-on

override-off:
	python3 -m sanctum_suite.cli override-off

clean:
	rm -rf .pytest_cache __pycache__ build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete