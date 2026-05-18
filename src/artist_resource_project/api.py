from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .intake_service import process_intake_submission


def create_app() -> FastAPI:
    app = FastAPI(
        title="Artist Resource Intake API",
        version="0.1.0",
        description="Webhook endpoint for Framer intake forms and automated draft shortlist emails.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/intake")
    async def intake(
        request: Request,
        x_intake_secret: str | None = Header(default=None, alias="X-Intake-Secret"),
    ) -> JSONResponse:
        _verify_secret(x_intake_secret)
        payload = await _read_payload(request)
        result = process_intake_submission(payload, send_email=True)
        status_code = 200 if result.get("email_sent") or result.get("email_error") else 200
        return JSONResponse(result, status_code=status_code)

    @app.post("/v1/intake/preview")
    async def intake_preview(
        request: Request,
        x_intake_secret: str | None = Header(default=None, alias="X-Intake-Secret"),
    ) -> JSONResponse:
        _verify_secret(x_intake_secret)
        payload = await _read_payload(request)
        result = process_intake_submission(payload, send_email=False)
        return JSONResponse(result)

    return app


app = create_app()


def run_api() -> None:
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("artist_resource_project.api:app", host="0.0.0.0", port=port, reload=False)


def _verify_secret(provided: str | None) -> None:
    expected = os.getenv("INTAKE_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="INTAKE_WEBHOOK_SECRET is not configured")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid intake secret")


async def _read_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        return body

    form = await request.form()
    if not form:
        raise HTTPException(status_code=400, detail="Expected JSON or form-encoded body")
    return {key: form.get(key) for key in form.keys()}
