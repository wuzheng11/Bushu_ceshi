FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY backend ./backend
COPY auth_server ./auth_server
COPY database ./database
COPY sample_data ./sample_data
COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --from=frontend-build /app/dist /usr/share/nginx/html

RUN rm -f /etc/nginx/sites-enabled/default \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/uploads /app/exports /app/workspace \
    && chown -R appuser:appuser /app /usr/share/nginx/html \
        /var/log/nginx /var/lib/nginx /var/cache/nginx \
    && chmod +x /usr/local/bin/entrypoint.sh

USER appuser

EXPOSE 8080 8000 8001

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
