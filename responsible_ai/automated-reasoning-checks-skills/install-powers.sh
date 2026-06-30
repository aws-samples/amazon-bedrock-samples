#!/usr/bin/env bash
# Install the Automated Reasoning Kiro Powers into ~/.kiro/powers (global) or .kiro/powers (local).
# Powers are generated from the SKILL.md files — run `uv run scripts/sync_powers.py` first if you edited a skill.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POWERS_DIR="$SCRIPT_DIR/powers"

SCOPE="global"
for arg in "$@"; do
  case "$arg" in
    -l|--local)  SCOPE="local"  ;;
    -g|--global) SCOPE="global" ;;
    -h|--help)
      echo "Usage: ./install-powers.sh [-g|--global] [-l|--local]"
      echo "  -g  install to ~/.kiro/powers (default)"
      echo "  -l  install to ./.kiro/powers (project-local)"
      exit 0 ;;
  esac
done

if [[ "$SCOPE" == "global" ]]; then
  DEST="$HOME/.kiro/powers"
else
  DEST="$PWD/.kiro/powers"
fi

if [[ ! -d "$POWERS_DIR" ]]; then
  echo "No powers/ dir found. Run: uv run scripts/sync_powers.py" >&2
  exit 1
fi

mkdir -p "$DEST"
count=0
for power in "$POWERS_DIR"/*/; do
  name="$(basename "$power")"
  [[ -f "$power/POWER.md" ]] || continue
  rm -rf "${DEST:?}/$name"
  cp -r "$power" "$DEST/$name"
  echo "  installed $name"
  count=$((count + 1))
done

echo "Installed $count powers to $DEST"
echo "Open Kiro and trigger one by intent, e.g. \"create an automated reasoning policy from this doc\"."
