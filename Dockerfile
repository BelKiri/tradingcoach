FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1 required by pandas/numpy at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tradecoach/ ./tradecoach/

RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app

EXPOSE 8000

USER app

CMD ["uvicorn", "tradecoach.main:app", "--host", "0.0.0.0", "--port", "8000"]
