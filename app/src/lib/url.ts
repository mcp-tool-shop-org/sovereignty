// Safe URL helpers — defense-in-depth against XSS via daemon-supplied URLs.
// Even though the daemon is bound to 127.0.0.1 with bearer-token auth, an
// attacker who compromises the daemon could inject a `javascript:` href into
// SSE payloads that pre-fill round status. React does NOT auto-sanitize
// href attributes, so we validate explicitly at render time.

const SAFE_SCHEMES = new Set(["http:", "https:"]);

/** Returns true if `url` is a well-formed http(s) URL. Used to guard
 *  external links rendered from daemon-supplied data (e.g. explorer_url).
 *  Rejects javascript:, data:, file:, vbscript:, and malformed strings. */
export function isSafeExplorerUrl(url: string | undefined | null): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return SAFE_SCHEMES.has(parsed.protocol);
  } catch {
    return false;
  }
}
