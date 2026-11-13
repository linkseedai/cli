#!/usr/bin/env node
"use strict";

const path = require("path");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);

process.env.LINKSEED_CLI_RUN = "1";
require("./install.js").install();

const binaryName = process.platform === "win32" ? "linkseed.exe" : "linkseed";
const binary = path.join(__dirname, "..", "bin", binaryName);
const result = spawnSync(binary, args, { stdio: "inherit" });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
