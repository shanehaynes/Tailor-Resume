#!/usr/bin/env bash
# Checks system prerequisites and prints install commands for anything missing.
cd "$(dirname "$0")/.."
ok=1
check() { if command -v "$1" >/dev/null; then echo "ok      $1"; else echo "MISSING $1  ->  macOS: $2   Linux: $3"; ok=0; fi; }
if [[ $(uname -s) == Darwin ]]; then
  if xcode-select -p >/dev/null 2>&1; then echo "ok      Xcode Command Line Tools"; else echo "MISSING Xcode Command Line Tools  ->  xcode-select --install"; ok=0; fi
  check brew    "see https://brew.sh"    "(not needed)"
fi
check uv        "brew install uv"        "curl -LsSf https://astral.sh/uv/install.sh | sh"
check pdftotext "brew install poppler"   "sudo apt-get install -y poppler-utils"
check curl      "(preinstalled)"         "sudo apt-get install -y curl"
check xz        "brew install xz"        "sudo apt-get install -y xz-utils"
check git       "xcode-select --install" "sudo apt-get install -y git"
check gh        "brew install gh"        "see https://cli.github.com"
# node runs the git guard hook: recommended, not required.
if command -v node >/dev/null; then echo "ok      node"; else echo "warn    node (optional; the git guard hook needs it)  ->  macOS: brew install node   Linux: sudo apt-get install -y nodejs"; fi
if [[ -x bin/typst ]]; then echo "ok      $(bin/typst --version) (bin/)"; else echo "MISSING bin/typst -> run: make setup"; ok=0; fi
[[ $ok == 1 ]] && echo "All prerequisites present." || exit 1
