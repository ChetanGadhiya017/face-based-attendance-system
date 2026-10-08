FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MODELS_DIR=/app/models
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY attendance ./attendance
COPY wsgi.py .
# Bake the face models into the image (≈38 MB) so containers start offline.
RUN FLASK_APP=wsgi flask download-models

RUN useradd --create-home app && mkdir -p /app/instance && chown -R app /app
USER app
VOLUME ["/app/instance"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
