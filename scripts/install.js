#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const pkg = require("../package.json");
const VERSION = pkg.version;
const REPO = repoSlug(pkg.repository && pkg.repository.url);

const PLATFORM = { darwin: "darwin", linux: "linux", win32: "windows" };
const ARCH = { x64: "amd64", arm64: "arm64" };

function repoSlug(url) {
  const match = String(url || "").match(
    /github\.com[:/]([^/]+)\/([^/#]+?)(?:\.git)?(?:[/?#].*)?$/
  );
  if (!match) {
    throw new Error("package.json repository.url must be a github.com repository");
  }
  return `${match[1]}/${match[2]}`;
}

function archiveName(platformName, archName) {
  const extension = platformName === "windows" ? ".zip" : ".tar.gz";
  return `linkseed-${VERSION}-${platformName}-${archName}${extension}`;
}

function expectedChecksum(name) {
  const checksumsPath = path.join(__dirname, "..", "checksums.txt");
  const content = fs.readFileSync(checksumsPath, "utf8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const separator = trimmed.indexOf("  ");
    if (separator === -1) continue;
    const hash = trimmed.slice(0, separator);
    const fileName = trimmed.slice(separator + 2);
    if (fileName === name) return hash;
  }
  throw new Error(
    `No checksum for ${name}. Publish that archive to ${REPO} before installing.`
  );
}

function verifyChecksum(filePath, expected) {
  if (!/^[0-9a-f]{64}$/i.test(expected)) {
    throw new Error("Checksum must be a 64-character SHA-256 hex digest");
  }
  const hash = crypto.createHash("sha256");
  const fd = fs.openSync(filePath, "r");
  try {
    const buffer = Buffer.alloc(64 * 1024);
    let bytesRead = 0;
    while ((bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) {
      hash.update(buffer.subarray(0, bytesRead));
    }
  } finally {
    fs.closeSync(fd);
  }
  const actual = hash.digest("hex");
  if (actual.toLowerCase() !== expected.toLowerCase()) {
    throw new Error(`Checksum mismatch for ${path.basename(filePath)}`);
  }
}

function download(url, destPath) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || parsed.hostname !== "github.com") {
    throw new Error(`Download host not allowed: ${parsed.hostname}`);
  }
  execFileSync(
    "curl",
    [
      "--fail",
      "--location",
      "--silent",
      "--show-error",
      "--connect-timeout",
      "10",
      "--max-time",
      "120",
      "--max-redirs",
      "3",
      "--output",
      destPath,
      url,
    ],
    { stdio: ["ignore", "ignore", "pipe"] }
  );
}

function extract(archivePath, destDir, platformName) {
  if (platformName === "windows") {
    execFileSync(
      "tar",
      ["-xf", archivePath, "-C", destDir],
      { stdio: "ignore" }
    );
    return;
  }
  execFileSync("tar", ["-xzf", archivePath, "-C", destDir], { stdio: "ignore" });
}

function install() {
  const platformName = PLATFORM[process.platform];
  const archName = ARCH[process.arch];
  if (!platformName || !archName) {
    throw new Error(`Unsupported platform: ${process.platform}-${process.arch}`);
  }

  const name = archiveName(platformName, archName);
  const url =
    `https://github.com/${REPO}/releases/download/v${VERSION}/${name}`;
  const binaryName = process.platform === "win32" ? "linkseed.exe" : "linkseed";
  const binDir = path.join(__dirname, "..", "bin");
  const dest = path.join(binDir, binaryName);
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "linkseed-cli-"));
  const archivePath = path.join(tmpDir, name);

  try {
    download(url, archivePath);
    verifyChecksum(archivePath, expectedChecksum(name));
    extract(archivePath, tmpDir, platformName);
    const extracted = path.join(tmpDir, binaryName);
    if (!fs.existsSync(extracted)) {
      throw new Error(`Archive ${name} does not contain ${binaryName}`);
    }
    fs.mkdirSync(binDir, { recursive: true });
    fs.copyFileSync(extracted, dest);
    fs.chmodSync(dest, 0o755);
    console.log(`linkseed v${VERSION} installed`);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

function main() {
  const isNpxPostinstall =
    process.env.npm_command === "exec" && !process.env.LINKSEED_CLI_RUN;
  if (isNpxPostinstall) return;

  try {
    install();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Failed to install linkseed: ${message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { install, repoSlug, archiveName, expectedChecksum };
