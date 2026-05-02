r"""Mechanical pin: every SovError factory's hint names a command.

Stage 8-C amend (Wave 11 Pin B). Walks ``sov_cli/errors.py`` AST, finds
every ``def *_error(...)`` function that returns a ``SovError(...)`` call,
extracts the ``hint`` kwarg's string-literal value (or the concatenation
of string literals — the factory pattern), and asserts the resolved hint
contains at least 2 backticks (a closing pair — ``\`cmd\```). Single-
backtick hints are broken markdown; absent or empty hints are skipped
(those are flagged by the recovery-hint coverage audit, a separate
concern).

Factories whose hint is dynamically constructed (f-strings, .format(),
runtime concatenation) cannot be statically resolved; this test records
them in ``FACTORIES_DYNAMIC_HINTS`` for manual coordinator audit rather
than producing a false-pass or false-fail.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ERRORS_PATH = Path(__file__).resolve().parent.parent / "sov_cli" / "errors.py"

# Factories whose hint is dynamically constructed and CANNOT be statically
# asserted. Recorded so the test surfaces them rather than silently
# skipping; coordinator review reads this list for manual hint-format
# audit. If a factory moves out of this set (hint becomes static), it
# must drop from this list AND start passing the test.
FACTORIES_DYNAMIC_HINTS: set[str] = set()


def _resolve_string_literal(node: ast.AST) -> str | None:
    """Resolve a string-literal expression to its concrete value.

    Handles:
      - ``ast.Constant(value=str)``
      - ``ast.JoinedStr`` → returns ``None`` (f-string is dynamic)
      - ``ast.BinOp(+)`` of string literals → concatenates recursively
      - parenthesized ``("a" "b")`` Python implicit-concat → the parser
        folds these into a single ``Constant`` so it is handled trivially.

    Anything else returns ``None`` → caller treats as dynamic.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_string_literal(node.left)
        right = _resolve_string_literal(node.right)
        if left is None or right is None:
            return None
        return left + right
    return None


def _collect_factories() -> list[tuple[str, str]]:
    """Walk errors.py AST and yield ``(factory_name, hint_text)`` pairs.

    Only collects factories whose hint can be statically resolved AND is
    non-empty. Dynamic-hint factories are added to
    ``FACTORIES_DYNAMIC_HINTS`` for manual review.

    A "factory" is any module-level ``def *_error(...)`` function that
    returns ``SovError(...)``. Multiple branches (if/elif) may each build
    their own ``SovError`` with a per-branch hint — every static one is
    collected so a regression in any branch surfaces.
    """
    source = ERRORS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ERRORS_PATH))

    out: list[tuple[str, str]] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.endswith("_error"):
            continue

        for sub in ast.walk(node):
            if not isinstance(sub, ast.Return):
                continue
            if not isinstance(sub.value, ast.Call):
                continue
            call = sub.value
            callee = call.func
            callee_name = callee.id if isinstance(callee, ast.Name) else None
            if callee_name != "SovError":
                continue
            hint_node: ast.AST | None = None
            for kw in call.keywords:
                if kw.arg == "hint":
                    hint_node = kw.value
                    break
            if hint_node is None:
                # SovError's hint kwarg is required for operator-facing
                # factories; a missing hint surfaces as an empty entry
                # so the assertion below catches it.
                out.append((node.name, ""))
                continue
            resolved = _resolve_string_literal(hint_node)
            if resolved is None:
                FACTORIES_DYNAMIC_HINTS.add(node.name)
                continue
            if resolved == "":
                # Empty hint = no command claimed; skip — the recovery-
                # hint coverage audit handles missing-hint factories
                # separately.
                continue
            out.append((node.name, resolved))

    return out


_COLLECTED = _collect_factories()


@pytest.mark.parametrize(
    ("factory_name", "hint_text"),
    _COLLECTED,
    ids=[f for f, _ in _COLLECTED],
)
def test_hint_contains_backticked_command(factory_name: str, hint_text: str) -> None:
    r"""Every static-hint SovError factory names a command in backticks.

    A paired ``\`cmd\``` requires 2 backticks. Single backtick = broken
    markdown. The 2-backtick floor is intentionally minimal: some hints
    contain MULTIPLE commands (``\`a\` then \`b\```), and we don't care
    which pattern — only that AT LEAST one paired pair exists.
    """
    assert hint_text, f"factory {factory_name!r} returned SovError with no hint kwarg"
    n_backticks = hint_text.count("`")
    assert n_backticks >= 2, (
        f"factory {factory_name!r} hint has {n_backticks} backtick(s); "
        f"need >= 2 for a paired `command` markdown span. "
        f"Hint text: {hint_text!r}"
    )


def test_dynamic_hint_factories_are_tracked() -> None:
    """Surface dynamic-hint factories for manual coordinator audit.

    Not a hard fail — informational. If ``FACTORIES_DYNAMIC_HINTS``
    grows, coordinator inspects to confirm each entry is genuinely
    dynamic (vs. a refactor candidate that should land static).
    """
    if FACTORIES_DYNAMIC_HINTS:
        print(
            "Factories with dynamically constructed hints "
            "(skipped by static gate, manual audit required):"
        )
        for name in sorted(FACTORIES_DYNAMIC_HINTS):
            print(f"  - {name}")
