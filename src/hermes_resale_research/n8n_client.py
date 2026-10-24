"""Small transport client for the optional local n8n workflow.

This module deliberately does not evaluate or transform resale data.  The
caller supplies the already validated Phase 1 JSON contract and this client
only transports it to n8n.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_N8N_URL = "http://localhost:5678/webhook/hermes-resale-evaluate"
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class N8nResponse:
    """Compact, JSON-serializable result of one webhook request."""

    ok: bool
    status_code: int | None = None
    data: Any = None
    error: Mapping[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"ok": self.ok, "status_code": self.status_code}
        if self.ok:
            result["data"] = self.data
        else:
            result["error"] = dict(self.error or {})
        return result


def webhook_url() -> str:
    """Return the n8n endpoint without coupling it to workflow logic."""
    return os.environ.get("N8N_RESALE_WEBHOOK_URL", DEFAULT_N8N_URL)


def post_evaluation(payload: Mapping[str, Any], *, url: str | None = None,
                    timeout: float | None = None) -> N8nResponse:
    """POST a validated evaluation contract and safely decode n8n's response."""
    if not isinstance(payload, Mapping):
        return N8nResponse(False, error={"code": "INVALID_PAYLOAD", "message": "payload must be a JSON object"})
    endpoint = url or webhook_url()
    try:
        body = json.dumps(dict(payload), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        return N8nResponse(False, error={"code": "INVALID_PAYLOAD", "message": "payload is not JSON serializable"})
    request = Request(endpoint, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urlopen(request, timeout=timeout or float(os.environ.get("N8N_RESALE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))) as response:
            status = response.status
            raw = response.read()
    except HTTPError as exc:
        return N8nResponse(False, exc.code, error={"code": "HTTP_ERROR", "message": f"n8n returned HTTP {exc.code}"})
    except (URLError, TimeoutError, OSError, ValueError):
        return N8nResponse(False, error={"code": "CONNECTION_ERROR", "message": "could not connect to n8n webhook"})
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return N8nResponse(False, status, error={"code": "MALFORMED_RESPONSE", "message": "n8n response was not valid JSON"})
    return N8nResponse(True, status, data=data)
