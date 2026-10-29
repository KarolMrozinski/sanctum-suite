#!/usr/bin/env bash
set -e

MODEL_DIR="$(dirname "$0")"
SELECTED_MODEL="${1:-llama3}" # Domyślnie Llama 3.2 3B

echo "=== SANCTUM SUITE: MENEDŻER POBIERANIA MODELI AI ==="

case "$SELECTED_MODEL" in
    "llama3")
        MODEL_FILE="$MODEL_DIR/llama-3.2-3b-instruct.Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
        echo "[INFO] Wybrano model: Llama 3.2 3B Instruct"
        ;;
    "gemma2")
        MODEL_FILE="$MODEL_DIR/gemma-2-9b-it.Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/bartowski/gemma-2-9b-it-GGUF/resolve/main/gemma-2-9b-it-Q4_K_M.gguf"
        echo "[INFO] Wybrano model: Google Gemma 2 9B IT"
        ;;
    "qwen25")
        MODEL_FILE="$MODEL_DIR/qwen-2.5-7b-instruct.Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
        echo "[INFO] Wybrano model: Alibaba Qwen 2.5 7B Instruct"
        ;;
    "gemma3")
        MODEL_FILE="$MODEL_DIR/gemma-3-model.Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/bartowski/gemma-3-GGUF/resolve/main/gemma-3-model-Q4_K_M.gguf"
        echo "[INFO] Wybrano model: Google Gemma 3"
        ;;
    "mistral24")
        MODEL_FILE="$MODEL_DIR/mistral-large-24b.Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/bartowski/Mistral-Large-Instruct-2407-GGUF/resolve/main/Mistral-Large-Instruct-2407-Q4_K_M.gguf"
        echo "[INFO] Wybrano model: Mistral Large 24B Instruct"
        ;;
    *)
        echo "[BŁĄD] Nieznany model: $SELECTED_MODEL"
        echo "Dostępne opcje: llama3, gemma2, qwen25, gemma3, mistral24"
        exit 1
        ;;
esac

if [ -f "$MODEL_FILE" ]; then
    echo "[INFO] Wybrany model GGUF już istnieje w katalogu: $MODEL_FILE"
    exit 0
fi

echo "[INFO] Pobieranie wybranego modelu z bezpiecznego źródła GGUF..."
curl -L -o "$MODEL_FILE" "$MODEL_URL"

echo "[SUKCES] Model został pomyślnie pobrany i jest gotowy do użycia!"