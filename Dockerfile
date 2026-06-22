# ---- builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY api/ ./api/

RUN adduser --disabled-password --gecos "" psxuser \
    && mkdir -p /home/psxuser/.psxdata/cache \
    && chown -R psxuser:psxuser /home/psxuser

ENV HOME=/home/psxuser
ENV PORT=8000
EXPOSE $PORT

USER psxuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health')"

CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1
