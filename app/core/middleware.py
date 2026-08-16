"""Small ASGI security middleware with no external infrastructure dependency."""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP bodies after measuring the actual received bytes."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {
            "POST",
            "PUT",
            "PATCH",
        }:
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self.max_bytes:
            await _send_json_error(send, 413, "Request body is too large.")
            return

        messages: list[Message] = []
        received_bytes = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            received_bytes += len(message.get("body", b""))
            if received_bytes > self.max_bytes:
                await _send_json_error(send, 413, "Request body is too large.")
                return
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)


class SecurityHeadersMiddleware:
    """Attach defensive browser headers and prevent caching of protected API data."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                _append_header(headers, existing, b"x-content-type-options", b"nosniff")
                _append_header(headers, existing, b"x-frame-options", b"DENY")
                _append_header(headers, existing, b"referrer-policy", b"no-referrer")
                _append_header(
                    headers,
                    existing,
                    b"permissions-policy",
                    b"camera=(), microphone=(), geolocation=()",
                )
                _append_header(
                    headers,
                    existing,
                    b"cross-origin-resource-policy",
                    b"same-origin",
                )
                if scope["type"] == "http" and str(scope.get("path", "")).startswith("/api/"):
                    _append_header(headers, existing, b"cache-control", b"no-store")
                    _append_header(
                        headers,
                        existing,
                        b"content-security-policy",
                        b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                    )
                if scope.get("scheme") == "https":
                    _append_header(
                        headers,
                        existing,
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains",
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name.lower() != b"content-length":
            continue
        try:
            return max(0, int(value))
        except ValueError:
            return None
    return None


def _append_header(
    headers: list[tuple[bytes, bytes]],
    existing: set[bytes],
    name: bytes,
    value: bytes,
) -> None:
    if name not in existing:
        headers.append((name, value))
        existing.add(name)


async def _send_json_error(send: Send, status_code: int, detail: str) -> None:
    payload = json.dumps({"detail": detail}, separators=(",", ":")).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})
