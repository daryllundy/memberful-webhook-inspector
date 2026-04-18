import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from rich.console import Console
from rich.panel import Panel

from .formatters import print_event
from .logger import log_invalid_attempt, log_verified_event
from .verify import verify_signature

SIGNATURE_HEADER = "X-Memberful-Webhook-Signature"
console = Console()
err_console = Console(stderr=True)
def load_settings() -> SimpleNamespace:
    load_dotenv()
    secret = os.getenv("MEMBERFUL_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError(
            "MEMBERFUL_WEBHOOK_SECRET is required. Copy .env.example to .env and set the Memberful signing secret."
        )
    return SimpleNamespace(
        secret=secret,
        port=int(os.getenv("PORT", "8000")),
        log_file=os.getenv("LOG_FILE", "./events.jsonl"),
    )


def mask_secret(secret: str) -> str:
    tail = secret[-4:] if len(secret) >= 4 else "****"
    return f"********...{tail} (loaded)"


def create_app() -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        body = "\n".join([
            "Memberful Webhook Inspector",
            f"Listening on http://localhost:{settings.port}/webhook",
            f"Logging to {settings.log_file}",
            f"Signing secret: {mask_secret(settings.secret)}",
        ])
        console.print(Panel(body, expand=False))
        console.print("Tip: expose this endpoint with `ngrok http %s`, then paste" % settings.port)
        console.print("the public URL into Memberful -> Settings -> Webhooks.\n")
        console.print("Waiting for events...")
        yield
    app = FastAPI(title="Memberful Webhook Inspector", lifespan=lifespan)
    app.state.settings = settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhook")
    async def webhook(request: Request) -> JSONResponse:
        body = await request.body()
        signature = request.headers.get(SIGNATURE_HEADER, "")
        if not signature:
            record_invalid(settings, request, "missing signature header", signature)
            return JSONResponse({"error": "missing signature header"}, status_code=401)
        if not verify_signature(body, signature, settings.secret):
            record_invalid(settings, request, "invalid signature", signature)
            return JSONResponse({"error": "invalid signature"}, status_code=401)

        try:
            raw_payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        payload = raw_payload if isinstance(raw_payload, dict) else {"payload": raw_payload}
        event = str(payload.get("event") or payload.get("type") or "unknown")
        log_verified_event(settings.log_file, event, payload)
        print_event({"event": event, **payload}, settings.log_file)
        return JSONResponse({"status": "ok"})

    return app


def record_invalid(settings: SimpleNamespace, request: Request, reason: str, signature: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source = request.client.host if request.client else "unknown"
    err_console.print(f"[{timestamp}] {reason} from {source}; signature={signature!r}")
    log_invalid_attempt(settings.log_file, reason, dict(request.headers))


try:
    app = create_app()
except RuntimeError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=app.state.settings.port)
