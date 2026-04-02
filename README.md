# FastAPI Production Starter

Step 1 scaffold for a production-grade FastAPI backend.

## Run locally

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Open: <http://127.0.0.1:8000/docs>

Health check: <http://127.0.0.1:8000/api/v1/health>

## Run tests

```bash
python -m pytest
```

Run only unit tests:

```bash
python -m pytest -m unit
```

Run only integration tests:

```bash
python -m pytest -m integration
```
