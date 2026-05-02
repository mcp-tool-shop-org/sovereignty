"""Structured-logging field registry for sov_daemon.

Every field used in daemon log emits is documented here. Field names are
stable contract; new daemon code consults this registry before inventing.

DAEMON-B-013 (Wave 9 Stage 7-B): structured JSON-lines log format. The
``--log-format=json`` flag at ``sov daemon start`` swaps the stderr
handler's formatter to ``JsonLineFormatter``; default stays human-readable
so a developer tailing the log doesn't get JSON soup.

Rule of thumb when adding emits:

* Use the namespaced-event-token style: ``anchor.submit``, ``anchor.success``,
  ``events.poll.failed``. The first whitespace-delimited token of
  ``record.getMessage()`` becomes the JSON ``"event"`` field.
* Pass structured context through ``extra={...}``. Do NOT interpolate via
  ``%s`` or f-string; the JSON formatter only promotes whitelisted fields
  from ``extra``.
* If you need a new field, add it to ``CONTEXT_FIELDS`` first so the JSON
  formatter knows to emit it.

Field registry:

* ``CORE_FIELDS`` — synthesised on every record (timestamp_iso, level,
  logger, event).
* ``CONTEXT_FIELDS`` — pulled from ``LogRecord.__dict__`` by the formatter
  when present. The set is intentionally small; extend it when v2.2 adds
  a new emit class.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

CORE_FIELDS: frozenset[str] = frozenset(
    {
        "timestamp_iso",
        "level",
        "logger",
        "event",
    }
)

CONTEXT_FIELDS: frozenset[str] = frozenset(
    {
        "account",  # XRPL classic address
        "txid",  # XRPL transaction hash
        "network",  # XRPLNetwork value
        "port",  # daemon port
        "pid",  # process id
        "round_key",  # "1".."15" or "FINAL"
        "game_id",  # "s{seed}"
        "error_code",  # DaemonErrorCode value
        "duration_ms",  # operation timing
        "client_ip",  # SSE client (always 127.0.0.1)
        "endpoint",  # HTTP path
        "status",  # HTTP status code
        "exception_type",  # type(exc).__name__
        "exception_detail",  # str(exc)
        "subscriber_count",  # SSE subscriber set size
        "max_subscribers",  # SSE subscriber cap
    }
)

KNOWN_FIELDS: frozenset[str] = CORE_FIELDS | CONTEXT_FIELDS


class JsonLineFormatter(logging.Formatter):
    """One-line JSON formatter for stdlib logging records.

    Emits a flat JSON object per record with the four core fields always
    present plus any whitelisted ``CONTEXT_FIELDS`` the emit site set via
    ``extra={...}``. Exception info is collapsed into ``exception_type``
    + ``exception_detail`` if not already supplied.

    The formatter is intentionally lossless on the message: even when no
    structured fields are supplied, ``message`` is preserved as the
    fallback ``event`` token (first whitespace-split word) so the
    emit-call form ``logger.info("legacy.event message %s", arg)`` still
    surfaces a sensible event field on the wire. New emits should use
    the ``logger.info("event.token", extra={...})`` form.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        first_token = message.split(" ", 1)[0] if message else record.name
        payload: dict[str, object] = {
            "timestamp_iso": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": first_token,
        }
        for field in CONTEXT_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        # Exception fallback: if the emit site used logger.exception(...)
        # without supplying structured fields, surface the type + message
        # so downstream log consumers don't have to parse the traceback.
        if record.exc_info and "exception_type" not in payload:
            exc_type, exc_value, _exc_tb = record.exc_info
            if exc_type is not None:
                payload["exception_type"] = exc_type.__name__
            if exc_value is not None:
                payload["exception_detail"] = str(exc_value)
        return json.dumps(payload, ensure_ascii=False)


__all__ = [
    "CONTEXT_FIELDS",
    "CORE_FIELDS",
    "JsonLineFormatter",
    "KNOWN_FIELDS",
]
