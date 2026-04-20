FROM python:3.11-slim
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e ".[api]"

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
