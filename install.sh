#!/bin/sh
# Install the linkseed command for macOS from a GitHub release.
# publish_cli.sh replaces __VERSION__ when exporting this file.
set -eu

REPO="linkseedai/cli"
VERSION="0.1.0-alpha"

if [ "$VERSION" = "__VERSION__" ]; then
  echo "This installer has no version. Use the copy exported to GitHub." >&2
  exit 1
fi

os=$(uname -s)
arch=$(uname -m)

case "$os" in
  Darwin) platform="darwin" ;;
  *)
    echo "This installer supports macOS. On Windows, run install.ps1 in PowerShell." >&2
    exit 1
    ;;
esac

case "$arch" in
  arm64|aarch64) cpu="arm64" ;;
  x86_64) cpu="amd64" ;;
  *)
    echo "Unsupported architecture: $arch" >&2
    exit 1
    ;;
esac

archive="linkseed-${VERSION}-${platform}-${cpu}.tar.gz"
base="https://github.com/${REPO}/releases/download/v${VERSION}"
checksum_url="https://raw.githubusercontent.com/${REPO}/v${VERSION}/checksums.txt"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

curl -fsSL "$checksum_url" -o "$tmp/checksums.txt"
curl -fsSL "${base}/${archive}" -o "$tmp/${archive}"

expected=$(awk -v name="$archive" '
  /^#/ || NF < 2 { next }
  $2 == name { print $1; exit }
' "$tmp/checksums.txt")

if [ -z "$expected" ]; then
  echo "No checksum for ${archive}." >&2
  exit 1
fi

actual=$(shasum -a 256 "$tmp/${archive}" | awk '{print $1}')
if [ "$actual" != "$expected" ]; then
  echo "Checksum mismatch for ${archive}." >&2
  exit 1
fi

tar -xzf "$tmp/${archive}" -C "$tmp"
if [ ! -f "$tmp/linkseed" ]; then
  echo "Archive ${archive} does not contain linkseed." >&2
  exit 1
fi

dest="${HOME}/.local/bin"
mkdir -p "$dest"
cp "$tmp/linkseed" "${dest}/linkseed"
chmod 755 "${dest}/linkseed"

echo "linkseed ${VERSION} installed to ${dest}/linkseed"
case ":${PATH}:" in
  *":${dest}:"*) ;;
  *)
    echo "Add this directory to PATH, then open a new terminal:"
    echo "  export PATH=\"${dest}:\$PATH\""
    ;;
esac
