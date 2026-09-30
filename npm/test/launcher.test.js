"use strict";

// Shape checks only. The download path hits GitHub Releases and is exercised
// by the post-publish smoke in .github/workflows/npm.yml.

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const pkg = require(path.join(root, "package.json"));

test("bin entry points at the launcher shim", () => {
  assert.equal(pkg.bin.sovereignty, "bin/sovereignty.js");
  assert.ok(fs.existsSync(path.join(root, pkg.bin.sovereignty)));
  assert.ok(pkg.dependencies["@mcptoolshop/npm-launcher"]);
});

test("shim derives version and tag from package.json", () => {
  const source = fs.readFileSync(path.join(root, "bin", "sovereignty.js"), "utf8");
  assert.match(source, /require\("\.\.\/package\.json"\)/);
  assert.match(source, /tag: `v\$\{version\}`/);
  assert.match(source, /owner: "mcp-tool-shop-org"/);
  assert.match(source, /repo: "sovereignty"/);
  assert.match(pkg.version, /^\d+\.\d+\.\d+$/);
});

test("published files include the shim", () => {
  assert.ok(pkg.files.includes("bin/"));
});
