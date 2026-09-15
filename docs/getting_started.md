# Getting Started

## Prerequisites

- Python 3.11+
- (Optional) Docker + Docker Compose

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running the App

```bash
streamlit run app.py
```

The app starts successfully even with an empty `.env` file — no agent
logic or LLM credentials are required to launch it. Streamlit will
print a local URL (default `http://localhost:8501`).

## Running with Docker

```bash
docker compose up --build
```

Then visit `http://localhost:8501`.

Notes:

- The project directory is bind-mounted to `/app` in the container, so
  edits to your code are reflected immediately without rebuilding the
  image.
- Environment variables are loaded from `.env` if it exists; copy
  `.env.example` to `.env` first if you want to set any (e.g. API
  keys). The container starts fine either way.
- Run in the background with `docker compose up -d --build`, view logs
  with `docker compose logs -f`, and stop everything with
  `docker compose down`.

## Running Tests

```bash
pytest
```

## Configuration

All configuration lives in `config/settings.py` and is loaded from
environment variables / `.env` (see `.env.example` for the full list).
Logging is configured centrally in `config/logging_config.py` and
initialized once in `app.py` via `setup_logging()`.
