#!/usr/bin/env bash
# Installs the pinned Typst binary into ./bin and syncs the Python env with uv.
# Idempotent. Never uses a globally installed typst.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="$(tr -d '[:space:]' < .typst-version)"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  TARGET=aarch64-apple-darwin ;;
  Darwin-x86_64) TARGET=x86_64-apple-darwin ;;
  Linux-x86_64)  TARGET=x86_64-unknown-linux-musl ;;
  Linux-aarch64|Linux-arm64) TARGET=aarch64-unknown-linux-musl ;;
  *) echo "Unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

ARCHIVE="typst-${TARGET}.tar.xz"
if [[ -x bin/typst ]] && bin/typst --version | grep -q "typst ${VERSION} "; then
  echo "typst ${VERSION} already installed in bin/"
else
  EXPECTED="$(grep " ${ARCHIVE}\$" scripts/typst-checksums.txt | cut -d' ' -f1)"
  [[ -n "$EXPECTED" ]] || { echo "No checksum recorded for ${ARCHIVE}" >&2; exit 1; }
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  echo "Downloading typst ${VERSION} (${TARGET})..."
  curl -fsSL -o "$TMP/$ARCHIVE" "https://github.com/typst/typst/releases/download/v${VERSION}/${ARCHIVE}"
  if command -v sha256sum >/dev/null; then ACTUAL="$(sha256sum "$TMP/$ARCHIVE" | cut -d' ' -f1)"
  else ACTUAL="$(shasum -a 256 "$TMP/$ARCHIVE" | cut -d' ' -f1)"; fi
  [[ "$ACTUAL" == "$EXPECTED" ]] || { echo "CHECKSUM MISMATCH for ${ARCHIVE}: got ${ACTUAL}" >&2; exit 1; }
  tar -xJf "$TMP/$ARCHIVE" -C "$TMP"
  mkdir -p bin && mv "$TMP/typst-${TARGET}/typst" bin/typst && chmod +x bin/typst
  echo "Installed $(bin/typst --version)"
fi

command -v uv >/dev/null || { echo "uv not found. Run 'make doctor' for install instructions." >&2; exit 1; }
uv sync --frozen
