.PHONY: help install test clean status run-cycle override-on override-off model-download

MODEL ?= llama3

help:
	@echo "=== SANCTUM SUITE: AUTOMATION & MANAGEMENT ==="
	@echo "  make install                 - Instalacja pakietu w trybie deweloperskim"
	@echo "  make test                    - Uruchomienie wszystkich testów"
	@echo "  make status                  - Sprawdzenie statusu systemu przez CLI"
	@echo "  make run-cycle               - Ręczne wyzwolenie cyklu agentów"
	@echo "  make override-on             - Włączenie blokady nadzoru operatora"
	@echo "  make override-off            - Wyłączenie blokady (tryb autonomiczny)"
	@echo "  make model-download MODEL=x  - Pobranie modelu (opcje: llama3, gemma2, qwen25, gemma3)"
	@echo "  make clean                   - Czyszczenie plików tymczasowych"

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

model-download:
	@chmod +x models/download_model.sh
	@./models/download_model.sh $(MODEL)