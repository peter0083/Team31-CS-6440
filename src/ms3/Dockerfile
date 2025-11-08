# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN adduser --disabled-password --gecos "" app && chown -R app:app /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python - <<'PY'\nimport requests,sys\n\ntry:\n  r=requests.get('http://127.0.0.1:8000/live',timeout=2)\n  sys.exit(0 if r.status_code==200 else 1)\nexcept Exception:\n  sys.exit(1)\nPY
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
