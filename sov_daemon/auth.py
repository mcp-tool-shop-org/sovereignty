"""Bearer-token authentication middleware for the daemon HTTP surface.

Single auth credential: a 256-bit URL-safe base64 token generated at
daemon start, written to ``.sov/daemon.json`` (read by CLI clients), and
held in memory by the running daemon. Per spec §7:

* Every endpoint EXCEPT ``OPTIONS`` preflight requires
  ``Authorization: Bearer <token>``.
* Missing token → HTTP 401 ``DAEMON_AUTH_MISSING``.
* Wrong token → HTTP 403 ``DAEMON_AUTH_INVALID``.
* Token comparison via ``secrets.compare_digest`` (constant-time) so a
  rogue local process can't time-side-channel the token byte by byte.

The middleware also injects all CORS headers on every response so
preflight ``OPTIONS`` requests (which the browser dispatches before the
actual auth'd request) round-trip correctly. Preflight bypasses auth
because browsers don't send ``Authorization`` on preflight by spec.

Implementation note
-------------------

Middleware is implemented as **pure ASGI** rather than via Starlette's
``BaseHTTPMiddleware``. The base class buffers the entire response
before forwarding — fine for plain JSON, fatal for the SSE
``/events`` stream which must yield each event frame as it's
generated. The pure-ASGI form intercepts the ``http.response.start``
message to inject CORS headers and otherwise lets every body chunk
flow through untouched.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# CORS posture is locked at the contract level (spec §7) at ``*`` because
# the Tauri webview origin differs across platforms (``tauri://localhost``
# on macOS/Linux, ``http://tauri.localhost`` on Windows) and the bearer
# token in the Authorization header is the actual auth gate. Restricting
# origin would block Wave 4 (Tauri shell) silently for no real security
# gain on a localhost-bound port.
_CORS_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "600",
}


def cors_headers() -> dict[str, str]:
    """Return a fresh copy of the CORS headers to attach to a response.

    A fresh copy each call so a handler that mutates the dict (rare,
    but possible) doesn't poison the module-level constant.
    """
    return dict(_CORS_HEADERS)


def _cors_header_pairs() -> list[tuple[bytes, bytes]]:
    """ASGI's wire form for headers: list of (name-bytes, value-bytes)."""
    return [(k.encode("latin-1"), v.encode("latin-1")) for k, v in _CORS_HEADERS.items()]


def _authorization_header(scope: Scope) -> str | None:
    """Pull the ``Authorization`` header out of an ASGI scope.

    Returns the decoded value (latin-1, ASCII-safe) or None.
    Header names in ASGI scopes are lowercase ``bytes``.
    """
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            try:
                decoded: str = value.decode("latin-1")
            except UnicodeDecodeError:
                return None
            return decoded
    return None


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    """Extract the token from an ``Authorization: Bearer <token>`` header.

    Returns None when the header is missing, empty, or doesn't follow the
    ``Bearer <token>`` shape. Whitespace is trimmed from the token half;
    the ``Bearer`` prefix is matched case-insensitively (RFC 6750 says
    case-insensitive).
    """
    if not authorization_header:
        return None
    parts = authorization_header.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


class BearerAuthMiddleware:
    """Pure-ASGI bearer-token + CORS middleware.

    OPTIONS preflight short-circuits with HTTP 204 + CORS headers and
    no auth check (browsers don't send ``Authorization`` on preflight).
    All other requests must carry a valid bearer token; the middleware
    injects the CORS headers into the eventual response by intercepting
    ``http.response.start`` messages and appending the header list.

    Streaming responses (e.g. SSE ``/events``) flow through unbuffered:
    each ``http.response.body`` message reaches the client immediately.
    """

    def __init__(self, app: ASGIApp, *, expected_token: str) -> None:
        """Bind the middleware to a single expected token.

        ``expected_token`` is the per-daemon-start token captured at
        ``run_foreground`` time. The middleware does NOT read
        ``.sov/daemon.json`` at request time — that would be a TOCTOU
        race with ``sov daemon stop`` removing the file mid-flight.
        """
        self.app = app
        self._expected_token = expected_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry. Auth-gates HTTP requests; passes through others.

        Lifespan / WebSocket scopes are forwarded unchanged. HTTP scopes
        run through the OPTIONS / token / forward path.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method == "OPTIONS":
            await _send_preflight(send)
            return

        token = _extract_bearer_token(_authorization_header(scope))
        if token is None:
            await _send_auth_failure(
                send,
                status_code=401,
                code="DAEMON_AUTH_MISSING",
                message=(
                    "missing Authorization header; daemon endpoints require Bearer token auth."
                ),
                hint="read .sov/daemon.json for the current token.",
            )
            return

        if not secrets.compare_digest(token, self._expected_token):
            await _send_auth_failure(
                send,
                status_code=403,
                code="DAEMON_AUTH_INVALID",
                message="Authorization token does not match the running daemon.",
                hint=("the daemon was restarted; re-read .sov/daemon.json for the new token."),
            )
            return

        # Inject CORS headers into the eventual response.start message
        # without buffering the body — pass-through for SSE.
        async def _wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Drop any CORS headers the inner app already set so we
                # don't end up with two ``Access-Control-Allow-Origin``
                # values on the wire.
                lowered = {
                    b"access-control-allow-origin",
                    b"access-control-allow-methods",
                    b"access-control-allow-headers",
                    b"access-control-max-age",
                }
                headers = [(n, v) for (n, v) in headers if n.lower() not in lowered]
                headers.extend(_cors_header_pairs())
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, _wrapped_send)


async def _send_preflight(send: Send) -> None:
    """Emit 204 No Content with CORS headers — OPTIONS preflight reply."""
    await send(
        {
            "type": "http.response.start",
            "status": 204,
            "headers": _cors_header_pairs(),
        }
    )
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def _send_auth_failure(
    send: Send,
    *,
    status_code: int,
    code: str,
    message: str,
    hint: str,
) -> None:
    """Emit a structured-error JSON response with CORS headers attached.

    Same {code, message, hint} shape as ``sov_cli.errors.SovError`` so
    the CLI / Tauri shell can surface daemon errors via the same render
    path used for engine / transport errors.
    """
    body: dict[str, Any] = {"code": code, "message": message, "hint": hint}
    payload = json.dumps(body).encode("utf-8")
    headers = _cors_header_pairs() + [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload)).encode("ascii")),
    ]
    await send({"type": "http.response.start", "status": status_code, "headers": headers})
    await send({"type": "http.response.body", "body": payload, "more_body": False})


__all__ = [
    "BearerAuthMiddleware",
    "cors_headers",
]
