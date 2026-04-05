# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN addgroup --system app && adduser --system --ingroup app app

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/alembic.ini ./alembic.ini
COPY backend/app ./app
COPY backend/alembic ./alembic

RUN pip install --upgrade pip setuptools wheel \
    && pip install .

USER app

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,sys,urllib.request; p=os.getenv('PORT','10000'); u=f'http://127.0.0.1:{p}/health'; sys.exit(0 if urllib.request.urlopen(u, timeout=3).status==200 else 1)"

CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
