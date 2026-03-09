FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .

# FIX: Strip invalid trailing letters from version strings before pip install
# e.g. httpx==0.27.0e → httpx==0.27.0
RUN sed -i -E 's/(==[0-9]+\.[0-9]+\.[0-9]+)[a-zA-Z][a-zA-Z0-9]*/\1/g' requirements.txt \
    && pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser src/ ./src/

ENV PATH=/home/appuser/.local/bin:$PATH

RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]