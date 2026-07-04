# Shark Tank AI — Dockerfile
#
# Builds a container image that runs the Streamlit application. Used
# both standalone (`docker build` / `docker run`) and via
# docker-compose.yml, which additionally bind-mounts the project
# directory for live development.

FROM python:3.12-slim

# Prevent .pyc files and force stdout/stderr to be unbuffered so logs
# show up immediately in `docker compose logs` / `docker logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (minimal, kept slim on purpose). curl is needed
# for the HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first so this layer is cached and only
# rebuilds when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application. In local development this is
# overridden by the bind mount configured in docker-compose.yml, so
# code changes on the host are picked up without rebuilding the image.
COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# CMD (not ENTRYPOINT) so docker-compose.yml or `docker run ... <cmd>`
# can override it cleanly if ever needed. runOnSave + fileWatcherType=poll
# give a smooth dev experience when the source is bind-mounted from the
# host (inotify events don't always propagate reliably across the
# host/container boundary, so polling is the safer default here).
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.runOnSave=true", "--server.fileWatcherType=poll"]
