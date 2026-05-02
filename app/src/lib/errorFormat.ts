// errorFormat — typed-error consumer for DaemonError + ShellError payloads.
//
// Pre-Stage-C every error site used `setError(String(e))`, which on a thrown
// Error object yields `"Error: <message>"` and silently drops the typed
// `DaemonError.hint` recovery copy the daemon emits. WEB-UI-C-007.
//
// This helper accepts:
//   - a raw `unknown` (Error, string, etc.)
//   - a JSON-string body that round-trips a `{ code, message, hint }` shape
//   - the parsed object directly
// and returns a normalized `{ message, hint? }` pair the UI can render side
// by side. Hint defaults to `undefined` so callers can use truthy checks.

export interface FormattedError {
  message: string;
  hint?: string;
}

interface MaybeTypedError {
  code?: unknown;
  message?: unknown;
  hint?: unknown;
}

function isTypedError(value: unknown): value is MaybeTypedError {
  if (value === null || typeof value !== "object") return false;
  const obj = value as MaybeTypedError;
  return typeof obj.message === "string" || typeof obj.code === "string";
}

export function formatError(input: unknown): FormattedError {
  if (input == null) return { message: "Unknown error" };

  // Direct typed-error object (e.g. parsed daemon response body, or a Tauri
  // ShellError relay).
  if (isTypedError(input)) {
    const message =
      typeof input.message === "string" && input.message.length > 0
        ? input.message
        : typeof input.code === "string"
          ? input.code
          : "Unknown error";
    const hint = typeof input.hint === "string" && input.hint.length > 0 ? input.hint : undefined;
    return { message, hint };
  }

  // String — may be a JSON body forwarded from a fetch response. Try to
  // parse and re-route.
  if (typeof input === "string") {
    const trimmed = input.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      try {
        const parsed: unknown = JSON.parse(trimmed);
        if (isTypedError(parsed)) return formatError(parsed);
      } catch {
        // fall through
      }
    }
    return { message: input };
  }

  // Error — pull `.message` and stop.
  if (input instanceof Error) {
    return { message: input.message || String(input) };
  }

  return { message: String(input) };
}
