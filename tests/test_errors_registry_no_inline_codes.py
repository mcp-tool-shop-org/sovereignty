"""The ``sov_cli.errors`` module is the single source of truth for every
operator-visible error code. Every other site that needs to raise a
``SovError`` must call a factory in ``sov_cli/errors.py`` rather than
constructing one inline with a string-literal ``code`` kwarg.

Stage 7-B closed the daemon side after Wave 8 surfaced 8 inline
``code="..."`` literals in ``sov_daemon/server.py``. Stage 8-C (Wave 11)
extends the gate from a hardcoded file list to a recursive AST walk over
every ``.py`` under ``sov_daemon/`` and ``sov_cli/`` — Mike's
reinforcement after the third regression in the inline-codes family.
Otherwise a fourth regression is one wave away: a new daemon endpoint
file or a freshly-extracted CLI helper grows an inline ``SovError(code=
"...")`` and the enumerated list misses it.

The test pins the boundary mechanically: every ``SovError(...)`` call
with a string-literal ``code`` kwarg outside ``sov_cli/errors.py`` (the
registry itself) is an inline-code regression. Failure surfaces the
file path + line number + offending code so the regression can be lifted
into a factory immediately.

Implementation note: the test is a static AST walk, not an import /
runtime check. That keeps the test cheap to run (no daemon spin-up, no
network) and robust to refactors that move the emit sites — what matters
is the absence of the inline pattern, not where any specific call lives.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ERRORS_PY = REPO_ROOT / "sov_cli" / "errors.py"

# Source trees the AST walk audits. The registry file itself
# (``sov_cli/errors.py``) is the ONE place a string-literal ``code=`` is
# allowed; every other ``.py`` under these roots must route through a
# factory.
SCAN_ROOTS = (REPO_ROOT / "sov_daemon", REPO_ROOT / "sov_cli")


def _factory_codes_in_errors_py() -> set[str]:
    """Return the set of ``code="..."`` string literals appearing inside
    ``SovError(...)`` constructions in ``sov_cli/errors.py``.

    Used to surface the registry's known codes for diagnostic context;
    not part of the boundary assertion (which is purely site-of-call).
    """
    src = ERRORS_PY.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(ERRORS_PY))
    codes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
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


def _iter_python_sources() -> list[Path]:
    """Yield every ``.py`` file under SCAN_ROOTS, excluding ``__pycache__``.

    The registry file itself (``sov_cli/errors.py``) is included in the
    walk but exempted at the per-call check below — there's no point in
    excluding it at the file level since the per-call exemption is the
    rule we want to express.
    """
    out: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            out.append(path)
    return sorted(out)


def test_no_inline_sov_error_codes_outside_registry() -> None:
    """No ``SovError(code="...")`` with a string-literal code outside
    ``sov_cli/errors.py``.

    Recursively AST-walks every ``.py`` file under ``sov_daemon/`` and
    ``sov_cli/``. For each ``SovError(...)`` call, if the ``code`` kwarg
    is a string literal AND the file is not the registry itself, the
    call is an inline-code regression — fail with file path + line number
    + the offending code so the fix is mechanical: lift the literal into
    a ``<concept>_error`` factory in ``sov_cli/errors.py`` and import +
    call it from the offending site.
    """
    violations: list[tuple[Path, int, str]] = []

    for source_path in _iter_python_sources():
        try:
            source = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(source_path))
        except SyntaxError:
            continue

        # The registry file is the one place a string-literal code is
        # allowed; skip the per-call check there but keep it in the walk
        # so a future move of the registry doesn't silently un-cover the
        # gate.
        if source_path.resolve() == ERRORS_PY.resolve():
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            callee_name: str | None = None
            if isinstance(func, ast.Name):
                callee_name = func.id
            elif isinstance(func, ast.Attribute):
                callee_name = func.attr
            if callee_name != "SovError":
                continue
            for kw in node.keywords:
                if kw.arg != "code":
                    continue
                if not isinstance(kw.value, ast.Constant):
                    continue
                value = kw.value.value
                if not isinstance(value, str):
                    continue
                violations.append((source_path, node.lineno, value))

    if violations:
        registry_codes = sorted(_factory_codes_in_errors_py())
        lines = [
            f"  {path.relative_to(REPO_ROOT)}:{lineno}  code={code!r}"
            for path, lineno, code in violations
        ]
        message = (
            "Inline SovError(code=...) literal(s) outside the registry "
            "(sov_cli/errors.py):\n"
            + "\n".join(lines)
            + "\n\nLift each literal into a <concept>_error factory in "
            "sov_cli/errors.py and import + call it from the offending "
            "site (see existing daemon_invalid_game_id_error et al. "
            "for the pattern).\n\n"
            f"Current registry codes: {registry_codes}"
        )
        raise AssertionError(message)


def test_factory_module_documents_daemon_error_section() -> None:
    """Pin the section header so future audits can find the daemon-error
    factory cluster by string-search alone (the alternative of grepping
    'def daemon_' is brittle when factory names diverge)."""
    src = ERRORS_PY.read_text(encoding="utf-8")
    assert re.search(r"v2\.1 daemon HTTP error registry", src), (
        "sov_cli/errors.py should mark the daemon-error factory cluster "
        "with a 'v2.1 daemon HTTP error registry' section header."
    )
