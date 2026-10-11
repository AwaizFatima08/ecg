#!/usr/bin/env bash
# Starts the Firebase emulators (functions, firestore, auth) for app testing on the LAN.
# Uses the real Claude reader if secrets/anthropic.env exists, else the mock reader.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PROVIDER=mock
if [ -f secrets/anthropic.env ]; then
  grep -E '^ANTHROPIC_API_KEY=' secrets/anthropic.env > functions/.secret.local
  PROVIDER=claude
fi
# Emulator-only parameters (App Check cannot be verified locally).
cat > functions/.env.local <<EOT
ECG_PROVIDER=$PROVIDER
ECG_MODEL=claude-opus-5-5
EOT
echo "Reader: $PROVIDER"
npm --prefix functions run build
ONLY=functions,auth
# The Firestore emulator (daily usage counter) needs Java 21+.
if java -version 2>&1 | grep -qE 'version "(2[1-9]|[3-9][0-9])'; then ONLY=functions,firestore,auth; fi
echo "Emulators: $ONLY"
exec firebase emulators:start --only "$ONLY" --project demo-ecg-reader
