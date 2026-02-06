#!/bin/bash
set -eu
set -o pipefail

echo "🔍 Scanning for secrets in public mirror scope..."

PATTERN_FILE="automation/redaction_patterns.txt"

PUBLISH_PATHS=(
  "contracts/"
  "protocols/"
  "phases/"
  "checks/"
  "automation/"
  "README.md"
  "changelog"
  "CONTRACT.md"
)

if [ ! -f "$PATTERN_FILE" ]; then
  echo "❌ Missing $PATTERN_FILE"
  exit 1
fi

# Build an alternation regex from non-empty lines (strip CR, join with |)
patterns="$(
  grep -vE '^[[:space:]]*$' "$PATTERN_FILE" \
  | tr -d '\r' \
  | paste -sd'|' -
)"

if [ -z "$patterns" ]; then
  echo "❌ No patterns found in $PATTERN_FILE"
  exit 1
fi

# Ignore matches explicitly marked as example placeholders
IGNORE_MARKER="EXAMPLE_SECRET:"

scan_path() {
  local path="$1"

  if [ -d "$path" ]; then
    # Print matches, then filter out approved example lines
    local matches
    matches="$(grep -RInE --exclude="SECURITY.md" --exclude="redaction_patterns.txt" "$patterns" "$path" 2>/dev/null || true)"
    matches="$(printf '%s\n' "$matches" | grep -vF "$IGNORE_MARKER" || true)"

    if [ -n "$matches" ]; then
      printf '%s\n' "$matches"
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  else
    local matches
    matches="$(grep -InE "$patterns" "$path" 2>/dev/null || true)"
    matches="$(printf '%s\n' "$matches" | grep -vF "$IGNORE_MARKER" || true)"

    if [ -n "$matches" ]; then
      printf '%s\n' "$matches"
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  fi
}

for path in "${PUBLISH_PATHS[@]}"; do
  [ -e "$path" ] || continue
  scan_path "$path"
done

echo "✅ No secrets found in publish scope"
