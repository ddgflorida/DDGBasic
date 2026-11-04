#!/usr/bin/env bash
# Build a standalone DbBasic executable with Nuitka (macOS/Linux)
# and install it somewhere on the PATH.
#
# Usage: ./compilenuitka.sh [install_dir]
#   install_dir defaults to ~/.local/bin

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$REPO_DIR/src"
BUILD_DIR="$REPO_DIR/build"
INSTALL_DIR="${1:-$HOME/.local/bin}"
PYTHON="${PYTHON:-python3}"

mkdir -p "$BUILD_DIR" "$INSTALL_DIR"

# Unpack once into a per-build cache folder instead of a fresh temp dir on
# every launch (otherwise each run pays several seconds of extraction).
BUILD_ID="$(date +%Y%m%d%H%M%S)"

cd "$SRC_DIR"

# The compiled binary can't read its own source, so it relies on
# Interpreter.BUILTIN_FN_NAMES for function references; make sure it's current.
"$PYTHON" - <<'EOF'
import inspect, re, sys
sys.argv = ['dbbasic']
import dbbasic
src = inspect.getsource(dbbasic.Interpreter._execute_function)
actual = set(re.findall(r"name == '([A-Z_][A-Z_0-9]*\$?)'", src))
listed = set(dbbasic.Interpreter.BUILTIN_FN_NAMES)
if actual != listed:
    print("BUILTIN_FN_NAMES in src/dbbasic.py is out of date.", file=sys.stderr)
    print("  missing:", sorted(actual - listed), file=sys.stderr)
    print("  extra:  ", sorted(listed - actual), file=sys.stderr)
    sys.exit(1)
EOF

"$PYTHON" -m nuitka \
    --onefile \
    --onefile-tempdir-spec="{CACHE_DIR}/dbbasic/$BUILD_ID" \
    --follow-imports \
    --assume-yes-for-downloads \
    --static-libpython=no \
    --output-dir="$BUILD_DIR" \
    --output-filename=dbbasic \
    dbbasic.py

cp "$BUILD_DIR/dbbasic" "$INSTALL_DIR/dbbasic"
chmod +x "$INSTALL_DIR/dbbasic"

echo "Installed: $INSTALL_DIR/dbbasic"
