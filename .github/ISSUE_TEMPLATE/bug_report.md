---
name: Bug report
about: Report a problem with sovereignty
labels: bug
---

## What did you try?

<!-- The command you ran, or the action you took at the table.
     Example: `sov end-round`, or "we tried to apologize twice in one game". -->

## What happened?

<!-- The actual output, error message, or behavior. Paste terminal output
     in a fenced block. -->

## What did you expect?

<!-- What you thought would happen instead. -->

## Environment

Please attach the JSON output of `sov support-bundle --json` (with seeds
redacted — they are by default). The schema is documented in
[docs/cli-json-output.md](../../docs/cli-json-output.md). This is the
canonical machine-readable diagnostic and gives us version, OS, Python,
and config in one paste.

```bash
sov support-bundle --json
```

If `support-bundle` itself is broken, fall back to:

- sovereignty version (`sov --version` or `pip show sovereignty-game`)
- OS + version (e.g. macOS 14.4, Ubuntu 22.04, Windows 11)
- Python version (`python --version`) — only if you installed via `pipx`/`pip`

## Reproduction steps

1.
2.
3.

<!-- The smaller and more deterministic the better. If a fresh `sov new`
     reproduces it, that's gold. If a saved game reproduces it, attach the
     `.sov/` directory if you can (or the relevant proof file). -->
