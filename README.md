# UAP Hotel Demo

A minimal HTTP-first hotel service exposing `/.well-known/uap`, plus a LangGraph agent that discovers capabilities via the UAP file.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
```

## Run the service

```bash
./.venv/bin/uvicorn app.main:app --reload
```

- UAP root: http://localhost:8000/.well-known/uap
- Booking module: http://localhost:8000/.well-known/booking.json
- OpenAPI: http://localhost:8000/openapi.json

## Run the agent

```bash
python agent/agent.py "Find available rooms for next weekend"
```

The agent uses `UAP_BASE_URL` from `.env` and calls `uap_discover` to read `/.well-known/uap` before selecting actions.
