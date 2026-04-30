# CLI JSON Output Schema

## Why JSON output?

Bug reports written as terminal screenshots are great for vibes and
terrible for triage. Versions get cropped, terminal themes hide red text,
and Unicode glyphs get mangled in copy-paste. The `--json` flag fixes
that: it produces a single compact envelope that captures the same
diagnostic data in a shape a human can read, a script can parse, and a
maintainer can replay.

The diagnostic commands `sov doctor`, `sov self-check`, and
`sov support-bundle` all accept `--json` and emit this envelope on stdout.
The default output (no flag) is unchanged — pretty rich-formatted text
for humans at the table.

## Worked example: `sov self-check --json`

Pipe it through `jq` to see the shape:

```bash
$ sov self-check --json | jq .
{
  "timestamp": "2026-04-30T12:34:56Z",
  "command": "sov self-check",
  "status": "ok",
  "fields": [
    {
      "name": "python_version",
      "status": "ok",
      "value": "3.12.4",
      "message": "Python 3.12.4 detected"
    },
    {
      "name": "sov_version",
      "status": "ok",
      "value": "2.0.0rc1",
      "message": "sovereignty-game 2.0.0rc1"
    },
    {
      "name": "wallet_seed_present",
      "status": "ok",
      "value": false,
      "message": "No wallet configured (Diary Mode disabled)"
    }
  ]
}
```

`status` rolls up to `"fail"` if any field failed, `"warn"` if any
warned, otherwise `"ok"`. That makes one-liners like
`sov self-check --json | jq -e '.status == "ok"'` work for CI smoke tests.

## Where to send the output

When you're filing a GitHub issue (`gh issue create`), the highest-signal
attachment you can include is `sov support-bundle --json`. It bundles
version, OS, Python, config, and the same field rollup as `self-check`
into a single JSON envelope. The bug-report template asks for it directly.

If a maintainer needs more — game state, logs, the lot — `sov
support-bundle` (without `--json`) writes a zip you can attach. The JSON
envelope is the canonical machine-readable diagnostic; the zip is the
"give me everything" escape hatch for hard reproductions.

This document is the **canonical schema** — both the CLI implementation
(engine domain) and any consumer (CI, incident-response runbooks, log
shippers, the bug-report template) MUST agree on this shape.

## When to use `--json`

- Attaching diagnostic output to a GitHub issue (preferred over screenshots).
- Piping into `jq` for scripted health checks (`sov doctor --json | jq ...`).
- CI smoke tests where a machine needs to assert "no field reports `fail`".
- Building dashboards or alerts on top of `sov support-bundle --json`.

For everyday human-readable output, omit the flag — the default is the
existing rich-formatted console output and is unaffected.

## Envelope shape

```json
{
  "timestamp": "2026-04-30T12:34:56Z",
  "command": "sov doctor",
  "status": "ok",
  "fields": [
    {
      "name": "python_version",
      "status": "ok",
      "value": "3.12.4",
      "message": "Python 3.12.4 detected"
    },
    {
      "name": "xrpl_endpoint",
      "status": "warn",
      "value": "https://s.altnet.rippletest.net:51234",
      "message": "Testnet endpoint reachable but slow (>2s)"
    }
  ]
}
```

## Field reference

| Key         | Type                          | Description                                                   |
|-------------|-------------------------------|---------------------------------------------------------------|
| `timestamp` | string (RFC 3339, UTC, `Z`)   | When the diagnostic ran. Always UTC, always `Z`-suffixed.     |
| `command`   | string                        | The invoking command (e.g. `"sov doctor"`).                   |
| `status`    | enum `"ok" \| "warn" \| "fail"` | Overall rollup. `fail` if any field is `fail`; `warn` if any field is `warn` and none are `fail`; otherwise `ok`. |
| `fields`    | array of objects              | One entry per check. See below.                               |

### `fields[]` entries

| Key       | Type                            | Description                                                      |
|-----------|---------------------------------|------------------------------------------------------------------|
| `name`    | string (snake_case stable id)   | Stable field identifier — never localized, never reformatted.    |
| `status`  | enum `"ok" \| "warn" \| "fail"` | Outcome of this individual check.                                |
| `value`   | any JSON value (string, number, bool, null, object, array) | The observed value. Type is field-specific; consumers MUST tolerate any JSON type. |
| `message` | string (optional)               | Human-readable explanation. Absent when no extra context exists. |

## Stability guarantees

- **Adding fields** to `fields[]` is non-breaking — consumers MUST tolerate
  unknown `name` values and skip them.
- **Adding new top-level keys** to the envelope is non-breaking — consumers
  MUST tolerate unknown keys.
- **Renaming or removing existing field names** IS breaking and only happens
  on a major version bump.
- **The `status` enum** will not gain new values without a major bump. If a
  future surface needs a fourth status, prefer composing via `message`.

## Redaction

The CLI redacts known-secret values before emitting JSON:

- `XRPL_SEED` env var, `wallet_seed.txt` content → never appears in `value`.
- Player names from `support-bundle` → optionally redacted via
  `--redact-names` (off by default; defer to user for private-play groups).

If you find a code path that leaks a secret into JSON output, treat it as a
security issue (see [SECURITY.md](../SECURITY.md#reporting-issues)).

## See also

- [SECURITY.md](../SECURITY.md) — the support-bundle JSON envelope is the
  canonical machine-readable diagnostic for incident response.
- [CONTRIBUTING.md](../CONTRIBUTING.md) — when adding a new diagnostic
  field, register its `name` here and add a test that asserts the JSON
  contract is preserved.
