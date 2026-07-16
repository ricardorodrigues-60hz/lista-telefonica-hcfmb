# 1. Imagem base oficial do Python optimizada (slim)
FROM python:3.11-slim

# Use a non-root user for improved security
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies (kept minimal) and install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt

# Copy application files and set ownership to the non-root user
COPY --chown=app:app . /app/

USER app

EXPOSE 8085

CMD sh -c "if [ \"$RUN_SEEDS\" = \"1\" ]; then python -m scripts.seed_mock; fi && uvicorn app.main:app --host 0.0.0.0 --port 8085"