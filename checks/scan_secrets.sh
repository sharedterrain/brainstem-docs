#!/bin/bash
set -euo pipefail

echo "🔍 Scanning for secrets in public mirror scope..."

PUBLISH_PATHS="contracts/ protocols/ phases/ checks/ automation/ README.md CHANGELOG.md CONTRACT.md"

if [ ! -f "automation/redaction_patterns.txt" ]; then
  echo "❌ Missing automation/redaction_patterns.txt"
  exit 1
fi

patterns=$(grep -vE '^[[:space:]]*

for path in $PUBLISH_PATHS; do
  if [ -e "$path" ]; then
    if grep -rE "$patterns" "$path" 2>/dev/null; then
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  fi
done

echo "✅ No secrets found in publish scope"
 automation/redaction_patterns.txt | tr '\n' '|' | sed 's/|/')

for path in $PUBLISH_PATHS; do
  if [ -e "$path" ]; then
    if grep -rE "$patterns" "$path" 2>/dev/null; then
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  fi
done

echo "✅ No secrets found in publish scope"
