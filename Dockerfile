# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir build && pip install --no-cache-dir .

# Stage 2: Production Minimal Image
FROM python:3.11-slim as runner

WORKDIR /app

# Utworzenie nieuprzywilejowanego użytkownika systemowego sanctum (Non-Root)
RUN useradd -m -u 10001 sanctumuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

RUN chown -R sanctumuser:sanctumuser /app
USER sanctumuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["sanctum", "serve", "--port", "8000"]