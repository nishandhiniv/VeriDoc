# syntax=docker/dockerfile:1
# VeriDoc: one image containing the web app and Tesseract OCR (NFR-13).
# Ubuntu 24.04 ships Tesseract 5.3 and Python 3.12 from the same, well-tested archive.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PORT=10000 \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-venv ca-certificates tesseract-ocr tesseract-ocr-eng fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

WORKDIR /app
COPY requirements.txt .
# The optional "ca" build secret is only used when building behind a TLS-inspecting
# proxy (as in the development sandbox). Render builds without it.
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY engine ./engine
COPY dataset ./dataset
COPY evaluation ./evaluation
COPY wsgi.py .

RUN useradd --create-home veridoc && mkdir -p /app/data && chown -R veridoc /app/data
USER veridoc

EXPOSE 10000
# One worker keeps SQLite simple and fits the free plan's memory; threads handle concurrent pages.
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 wsgi:app
