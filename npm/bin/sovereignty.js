#!/usr/bin/env node
"use strict";

// Downloads the SHA256-verified `sov` binary from the GitHub Release whose
// tag matches this package's version, then runs it with the given arguments.
// Asset names follow the release convention:
//   sovereignty-<version>-<os>-<arch>[.exe]  and  checksums-<version>.txt
const { version } = require("../package.json");

process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "sovereignty",
  owner: "mcp-tool-shop-org",
  repo: "sovereignty",
  version,
  tag: `v${version}`,
});

require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
