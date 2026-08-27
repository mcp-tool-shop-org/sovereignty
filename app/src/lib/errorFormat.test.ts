import { describe, expect, it } from "vitest";
import { formatError } from "./errorFormat";

describe("formatError (F-4cf7bf68)", () => {
  it("maps DaemonStartFailed code + stderr to Display message and stderr hint", () => {
    const formatted = formatError({
      code: "DaemonStartFailed",
      stderr: "port already in use",
    });
    expect(formatted.message).toMatch(/sov doctor/);
    expect(formatted.hint).toBe("port already in use");
  });

  it("maps SubprocessFailed timeout shape to recovery + stderr hint", () => {
    const formatted = formatError({
      code: "SubprocessFailed",
      exit_code: -1,
      stderr:
        "the `sov daemon` command did not respond within 10s. Run `sov daemon stop` then retry, or run `sov doctor` for diagnostics.",
    });
    expect(formatted.message).toMatch(/exit code -1/);
    expect(formatted.hint).toMatch(/sov doctor/);
  });

  it("prefers wire `message` when the shell serializes Display", () => {
    const formatted = formatError({
      code: "DaemonStartFailed",
      message: "Daemon start failed: boom. Run `sov doctor` for diagnostics.",
      stderr: "boom",
    });
    expect(formatted.message).toContain("sov doctor");
    expect(formatted.hint).toBe("boom");
  });

  it("parses a JSON-message Error into the coded payload", () => {
    const err = new Error(
      JSON.stringify({
        code: "ConfigFileMalformed",
        detail: "missing field `pid`",
      }),
    );
    const formatted = formatError(err);
    expect(formatted.message).toMatch(/sov daemon start/);
    expect(formatted.hint).toBe("missing field `pid`");
  });

  it("does not treat a plain Error as a typed payload", () => {
    const formatted = formatError(new Error("network down"));
    expect(formatted.message).toBe("network down");
    expect(formatted.hint).toBeUndefined();
  });

  it("surfaces ConfigSchemaUnsupported found/expected as hint", () => {
    const formatted = formatError({
      code: "ConfigSchemaUnsupported",
      found: 9,
      expected: 1,
    });
    expect(formatted.message).toMatch(/pip install -U/);
    expect(formatted.hint).toBe("found schema 9, expected 1");
  });
});
