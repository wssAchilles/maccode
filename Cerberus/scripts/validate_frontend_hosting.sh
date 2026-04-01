#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node is required" >&2
  exit 1
fi

resolve_default_frontend_url() {
  node <<'EOF'
const fs = require('fs')
const path = require('path')
const firebaseConfigPath = path.join(process.cwd(), 'firebase.json')
const config = JSON.parse(fs.readFileSync(firebaseConfigPath, 'utf8'))
const hosting = Array.isArray(config.hosting) ? config.hosting[0] : config.hosting
if (!hosting || !hosting.site) {
  process.exit(1)
}
process.stdout.write(`https://${hosting.site}.web.app`)
EOF
}

FRONTEND_URL="${1:-${FRONTEND_URL:-}}"
if [[ -z "${FRONTEND_URL}" ]]; then
  FRONTEND_URL="$(cd "${ROOT_DIR}" && resolve_default_frontend_url)"
fi
FRONTEND_URL="${FRONTEND_URL%/}"

require_header() {
  local headers="$1"
  local expected="$2"
  if ! grep -iq "^${expected}" <<<"${headers}"; then
    echo "missing header: ${expected}" >&2
    exit 1
  fi
}

echo "validating hosting url ${FRONTEND_URL}"

ROOT_HEADERS="$(curl -fsSIL "${FRONTEND_URL}/")"
ROOT_HTML="$(curl -fsSL "${FRONTEND_URL}/")"
MANIFEST_BODY="$(curl -fsSL "${FRONTEND_URL}/site.webmanifest")"
ROBOTS_BODY="$(curl -fsSL "${FRONTEND_URL}/robots.txt")"

require_header "${ROOT_HEADERS}" "content-security-policy:"
require_header "${ROOT_HEADERS}" "permissions-policy:"
require_header "${ROOT_HEADERS}" "referrer-policy: strict-origin-when-cross-origin"
require_header "${ROOT_HEADERS}" "strict-transport-security:"
require_header "${ROOT_HEADERS}" "x-content-type-options: nosniff"
require_header "${ROOT_HEADERS}" "x-frame-options: DENY"

if grep -Eiq 'localhost|127\.0\.0\.1' <<<"${ROOT_HTML}"; then
  echo "deployed HTML still contains local host references" >&2
  exit 1
fi

if ! grep -q '<link rel="manifest" href="/site.webmanifest"' <<<"${ROOT_HTML}"; then
  echo "manifest link missing from deployed HTML" >&2
  exit 1
fi

if ! grep -q 'User-agent: \*' <<<"${ROBOTS_BODY}"; then
  echo "robots.txt does not look valid" >&2
  exit 1
fi

if ! grep -q '"start_url": "/?workspace=overview"' <<<"${MANIFEST_BODY}"; then
  echo "site.webmanifest start_url is unexpected" >&2
  exit 1
fi

MAIN_ASSET_PATH="$(node -e "const html = process.argv[1]; const match = html.match(/\\/assets\\/index-[^\"']+\\.js/); if (!match) process.exit(1); process.stdout.write(match[0]);" "${ROOT_HTML}")"
ASSET_URL="$(node -e "const base = new URL(process.argv[1]); const asset = process.argv[2]; process.stdout.write(new URL(asset, base).toString())" "${FRONTEND_URL}/" "${MAIN_ASSET_PATH}")"
ASSET_HEADERS="$(curl -fsSIL "${ASSET_URL}")"
require_header "${ASSET_HEADERS}" "cache-control: public,max-age=31536000,immutable"

echo "hosting validation passed for ${FRONTEND_URL}"
