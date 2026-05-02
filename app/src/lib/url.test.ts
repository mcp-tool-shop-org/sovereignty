import { describe, expect, it } from "vitest";
import { isSafeExplorerUrl } from "./url";

describe("isSafeExplorerUrl — XSS defense for daemon-supplied URLs", () => {
  it("accepts https URLs", () => {
    expect(isSafeExplorerUrl("https://testnet.xrpl.org/transactions/ABC")).toBe(true);
  });

  it("accepts http URLs (localhost test environments)", () => {
    expect(isSafeExplorerUrl("http://localhost:8080/tx/123")).toBe(true);
  });

  it("rejects javascript: URLs", () => {
    expect(isSafeExplorerUrl("javascript:alert(document.cookie)")).toBe(false);
  });

  it("rejects javascript: with whitespace prefix", () => {
    // URL parser handles trimming; this still fails the http(s) scheme check.
    expect(isSafeExplorerUrl("  javascript:alert(1)")).toBe(false);
  });

  it("rejects data: URLs", () => {
    expect(isSafeExplorerUrl("data:text/html,<script>alert(1)</script>")).toBe(false);
  });

  it("rejects vbscript: URLs", () => {
    expect(isSafeExplorerUrl("vbscript:msgbox(1)")).toBe(false);
  });

  it("rejects file: URLs", () => {
    expect(isSafeExplorerUrl("file:///etc/passwd")).toBe(false);
  });

  it("rejects malformed URLs", () => {
    expect(isSafeExplorerUrl("not a url")).toBe(false);
    expect(isSafeExplorerUrl("//missing-scheme")).toBe(false);
  });

  it("rejects undefined / null / empty", () => {
    expect(isSafeExplorerUrl(undefined)).toBe(false);
    expect(isSafeExplorerUrl(null)).toBe(false);
    expect(isSafeExplorerUrl("")).toBe(false);
  });
});
