"""Stage 7-B amend (CLI-B-012): the daemon must not emit inline error
codes that bypass the ``sov_cli.errors`` registry.

The ``sov_cli.errors`` module is the single source of truth for every
operator-visible error code in v2.1. Two parallel surfaces emit them:

* CLI Typer commands raise via ``_fail(SovError(...))``.
* ``sov_daemon.server`` returns HTTP responses via ``_error_response(...)``.

Stage A landed the CLI side. Stage 7-B closes the daemon side: every
``code=`` literal in ``sov_daemon/server.py`` must come from a factory in
``sov_cli/errors.py`` (so the message + hint are humanised exactly once
and the TS ``DaemonErrorCode`` mirror has a single registry to enumerate
against).

The Wave 8 audit found 8 inline ``code="..."`` literals in server.py — this
test pins the post-amend posture: NO inline daemon error code outside the
factory registry. Adding a new code requires adding a factory FIRST, which
forces the humanisation discipline and the TS-mirror coordination.

Implementation note: the test is a static AST walk, not an import / runtime
check. That keeps the test cheap to run (no daemon spin-up, no network) and
robust to refactors that move the emit sites — what matters is the absence
of the inline pattern, not where any specific call lives.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DAEMON_SERVER = REPO_ROOT / "sov_daemon" / "server.py"
ERRORS_PY = REPO_ROOT / "sov_cli" / "errors.py"


# Codes that legitimately appear as string literals in server.py because
# they're being PASSED IN from a SovError factory (e.g.
# ``code=sov_err.code`` is fine; ``code="ANCHOR_FAILED"`` is not). The
# allowlist below names codes that MUST appear via factory call, never
# inline literal — anything in this set surfacing as an inline string in
# server.py fails the test.
DAEMON_ERROR_CODES_FROM_FACTORIES = {
    # Auth + transport (already factory-routed pre-Stage 7-B)
    "DAEMON_READONLY",
    "DAEMON_AUTH_MISSING",
    "DAEMON_AUTH_INVALID",
    "DAEMON_PORT_BUSY",
    # Validation + lookup (Stage 7-B amend, CLI-B-012)
    "INVALID_GAME_ID",
    "INVALID_ROUND",
    "INVALID_NETWORK",
    "GAME_NOT_FOUND",
    "PROOF_NOT_FOUND",
    "PROOF_UNREADABLE",
    # Anchor pipeline (Stage 7-B amend, CLI-B-012)
    "ANCHOR_FAILED",
    "XRPL_NOT_INSTALLED",
    "MAINNET_UNDERFUNDED",
    "MAINNET_FAUCET_REJECTED",
    # Wave-1 anchor lifecycle (factory-routed since v2.1 wave-2)
    "ANCHOR_PENDING",
}


def _factories_in_errors_py() -> set[str]:
    """Return the set of ``def <name>_error(...) -> SovError`` factory names
    declared in ``sov_cli/errors.py``."""
    src = ERRORS_PY.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(ERRORS_PY))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.endswith("_error"):
            names.add(node.name)
    return names


def _factory_codes_in_errors_py() -> set[str]:
    """Return the set of ``code="..."`` string literals appearing inside
    ``SovError(...)`` constructions in ``sov_cli/errors.py``.

    Used to assert every daemon-emitted code has a factory. The factory
    body looks like:

        return SovError(code="GAME_NOT_FOUND", message=..., hint=...)

    so the codes registry is the disjoint union of the literals across
    every factory body.
    """
    src = ERRORS_PY.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(ERRORS_PY))
    codes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # SovError(code="...", ...) or SovError(code='...', ...)
        func = node.func
        if isinstance(func, ast.Name) and func.id == "SovError":
            for kw in node.keywords:
                if (
                    kw.arg == "code"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)
                ):
                    codes.add(kw.value.value)
    return codes


def test_every_daemon_error_code_has_a_factory() -> None:
    """Every code in DAEMON_ERROR_CODES_FROM_FACTORIES must surface as a
    string literal inside a SovError(...) factory in sov_cli/errors.py.

    Drift mode: someone adds a new daemon-emitted code without a factory.
    This test fails BEFORE the inline-emit test catches it, with a hint
    pointing at the right file to fix.
    """
    factory_codes = _factory_codes_in_errors_py()
    missing = DAEMON_ERROR_CODES_FROM_FACTORIES - factory_codes
    assert not missing, (
        f"Missing factory in sov_cli/errors.py for daemon-emitted code(s): "
        f"{sorted(missing)}. Add a daemon_<concept>_error factory."
    )


@pytest.mark.skipif(
    not DAEMON_SERVER.exists(),
    reason="sov_daemon/server.py not present (pre-Wave-3 install)",
)
def test_daemon_server_has_no_inline_error_codes() -> None:
    """No inline ``code="..."`` literal in sov_daemon/server.py for any
    code that should come from a factory.

    Implementation: AST-walks server.py, collects every ``code="..."``
    string literal passed to a function call, and asserts the literal
    is NOT in DAEMON_ERROR_CODES_FROM_FACTORIES. The exception is the
    ``code=sov_err.code`` form (an attribute access, not a string
    literal) — that's the post-amend pattern and the AST walk skips it.
    """
    src = DAEMON_SERVER.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(DAEMON_SERVER))

    inline_violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "code":
                continue
            if not isinstance(kw.value, ast.Constant):
                continue
            value = kw.value.value
            if not isinstance(value, str):
                continue
            if value in DAEMON_ERROR_CODES_FROM_FACTORIES:
                inline_violations.append((node.lineno, value))

    assert not inline_violations, (
        "Inline daemon error code(s) bypass the sov_cli.errors registry:\n  "
        + "\n  ".join(f"line {ln}: code={code!r}" for ln, code in inline_violations)
        + "\n\nLift each into a daemon_<concept>_error factory in "
        + "sov_cli/errors.py and import + call it from sov_daemon/server.py "
        + "(see daemon_invalid_game_id_error et al. for the pattern)."
    )


def test_factory_module_documents_daemon_error_section() -> None:
    """Pin the section header so future audits can find the daemon-error
    factory cluster by string-search alone (the alternative of grepping
    'def daemon_' is brittle when factory names diverge)."""
    src = ERRORS_PY.read_text(encoding="utf-8")
    assert re.search(r"v2\.1 daemon HTTP error registry", src), (
        "sov_cli/errors.py should mark the daemon-error factory cluster "
        "with a 'v2.1 daemon HTTP error registry' section header."
    )
