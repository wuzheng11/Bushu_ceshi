#!/bin/sh
set -eu

ROLE="${APP_ROLE:-backend}"

if [ "$ROLE" = "web" ]; then
    exec nginx -g "daemon off; pid /tmp/nginx.pid;"
fi

python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

role = os.getenv("APP_ROLE", "backend")
if role == "auth":
    from auth_server.config import settings

    database_url = settings.database_url
else:
    from backend.app.config import settings

    database_url = settings.app_database_url

engine = create_engine(database_url, pool_pre_ping=True)
last_error = None
for attempt in range(1, 61):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print(f"MySQL is ready for {role}", flush=True)
        break
    except Exception as exc:
        last_error = exc
        print(f"Waiting for MySQL ({attempt}/60): {exc}", flush=True)
        time.sleep(2)
else:
    raise RuntimeError(f"MySQL did not become ready: {last_error}")
PY

if [ "$ROLE" = "backend" ] && [ "${SEED_ON_START:-false}" = "true" ]; then
    python -c "from backend.app.seed import seed_if_needed; seed_if_needed()"
fi

if [ "$ROLE" = "auth" ]; then
    exec uvicorn auth_server.main:app --host 0.0.0.0 --port 8001 --workers 1
fi

exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
