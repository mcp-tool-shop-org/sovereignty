# CLI JSON Output Schema

The diagnostic commands `sov doctor`, `sov self-check`, and
`sov support-bundle` accept a `--json` flag that emits a machine-readable
envelope on stdout. This document is the **canonical schema** — both the CLI
implementation (engine domain) and any consumer (CI, incident-response
runbooks, log shippers) MUST agree on this shape.

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
