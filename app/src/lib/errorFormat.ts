// errorFormat — typed-error consumer for DaemonError + ShellError payloads.
//
// Pre-Stage-C every error site used `setError(String(e))`, which on a thrown
// Error object yields `"Error: <message>"` and silently drops the typed
// `DaemonError.hint` recovery copy the daemon emits. WEB-UI-C-007.
//
// F-4cf7bf68: ShellError serializes as `{ code, message, ...variant fields }`.
// A string `code` without `message` still maps to Display/recovery; `stderr`
// and `detail` surface as the hint. `Error` instances are NOT treated as
// typed payloads just because they have `.message` — that blocked the
// JSON-body parse and `instanceof Error` branches.

export interface FormattedError {
  message: string;
  hint?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** Coded daemon/shell payload. Must have a string `code` and must NOT be an
 *  `Error` instance — every Error has `.message`, which is not a typed wire. */
function isCodedPayload(value: unknown): value is Record<string, unknown> {
  if (!isRecord(value)) return false;
  if (value instanceof Error) return false;
  return typeof value.code === "string";
}

function hintFromShellFields(obj: Record<string, unknown>): string | undefined {
  if (typeof obj.hint === "string" && obj.hint.length > 0) return obj.hint;
  if (typeof obj.stderr === "string" && obj.stderr.length > 0) return obj.stderr;
  if (typeof obj.detail === "string" && obj.detail.length > 0) return obj.detail;
  if (typeof obj.found === "number" && typeof obj.expected === "number") {
    return `found schema ${obj.found}, expected ${obj.expected}`;
  }
  return undefined;
}

/** Display/recovery copy for ShellError codes when the wire omitted `message`
 *  (old shell binary). Mirrors `app/src-tauri/src/commands.rs` Display. */
function messageForShellCode(obj: Record<string, unknown>): string {
  const code = obj.code as string;
  switch (code) {
    case "DaemonNotRunning":
      return "Daemon is not running. Start it with `sov daemon start`.";
    case "DaemonStartFailed":
      return `Daemon start failed: ${typeof obj.stderr === "string" ? obj.stderr : ""}. Run \`sov doctor\` for diagnostics.`;
    case "DaemonNotInstalled":
      return "Daemon is not installed. Install with `pip install 'sovereignty-game[daemon]'`.";
    case "ConfigFileMissing":
      return "Config file `.sov/daemon.json` is missing. Run `sov daemon start` to create it (or write the file manually).";
    case "ConfigFileMalformed":
      return `Config file \`.sov/daemon.json\` is malformed: ${typeof obj.detail === "string" ? obj.detail : ""}. Delete the file and run \`sov daemon start\` to regenerate.`;
    case "ConfigSchemaUnsupported":
      return `Config schema version ${obj.found} is unsupported (expected ${obj.expected}). Upgrade with \`pip install -U sovereignty-game\`.`;
    case "SubprocessFailed":
      return `The \`sov daemon\` command failed (exit code ${obj.exit_code}): ${typeof obj.stderr === "string" ? obj.stderr : ""}`;
    case "Panic":
      return typeof obj.message === "string" && obj.message.length > 0
        ? obj.message
        : "The Sovereignty shell crashed. Restart the app and run `sov doctor` for diagnostics.";
    default:
      return code;
  }
}

function formatCoded(obj: Record<string, unknown>): FormattedError {
  const message =
    typeof obj.message === "string" && obj.message.length > 0
      ? obj.message
      : messageForShellCode(obj);
  const hint = hintFromShellFields(obj);
  return hint ? { message, hint } : { message };
}

function tryParseJsonObject(text: string): unknown | undefined {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) return undefined;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return undefined;
  }
}

export function formatError(input: unknown): FormattedError {
  if (input == null) return { message: "Unknown error" };

  if (isCodedPayload(input)) return formatCoded(input);

  if (typeof input === "string") {
    const parsed = tryParseJsonObject(input);
    if (isCodedPayload(parsed)) return formatCoded(parsed);
    return { message: input };
  }

  if (input instanceof Error) {
    const parsed = tryParseJsonObject(input.message);
    if (isCodedPayload(parsed)) return formatCoded(parsed);
    return { message: input.message || String(input) };
  }

  return { message: String(input) };
}
