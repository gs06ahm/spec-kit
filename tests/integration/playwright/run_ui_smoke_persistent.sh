#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-ghsmoke}"
PROJECT_URL="${TEST_PROJECT_URL:-}"
SNAPSHOT_FILE="${SNAPSHOT_FILE:-/tmp/gh-project-smoke.yaml}"
MODE="smoke"
HEADED=false

usage() {
  cat <<EOF
Usage: $0 [--login] [--headed] [--project-url URL] [--session NAME] [--snapshot FILE]

Options:
  --login              Open persistent Playwright session for one-time GitHub MFA login
  --headed             Launch browser in headed mode (recommended for --login)
  --project-url URL    Project URL to validate (required for smoke mode, or set \$TEST_PROJECT_URL)
  --session NAME       Persistent Playwright session name (default: ${SESSION_NAME})
  --snapshot FILE      Snapshot output file (default: ${SNAPSHOT_FILE})
  -h, --help           Show help

Examples:
  # 1) One-time login (complete MFA in browser window)
  $0 --login --session ghsmoke

  # 2) Reuse saved auth/session for UI smoke
  $0 --session ghsmoke --project-url https://github.com/users/<you>/projects/<n>
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --login)
      MODE="login"
      shift
      ;;
    --headed)
      HEADED=true
      shift
      ;;
    --project-url)
      PROJECT_URL="$2"
      shift 2
      ;;
    --session)
      SESSION_NAME="$2"
      shift 2
      ;;
    --snapshot)
      SNAPSHOT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v playwright-cli >/dev/null 2>&1; then
  echo "playwright-cli is required but not found in PATH." >&2
  exit 1
fi

if [[ "${MODE}" == "login" ]]; then
  HEADED=true
fi

OPEN_ARGS=( -s="${SESSION_NAME}" open --persistent )
if [[ "${HEADED}" == "true" ]]; then
  OPEN_ARGS+=( --headed )
fi

if [[ "${MODE}" == "login" ]]; then
  echo "Opening persistent Playwright session '${SESSION_NAME}' for GitHub login..."
  playwright-cli "${OPEN_ARGS[@]}"
  playwright-cli -s="${SESSION_NAME}" goto "https://github.com/login"
  echo
  echo "Complete GitHub login + MFA in the opened browser."
  read -r -p "Press Enter after successful login to save session and close... "
  playwright-cli -s="${SESSION_NAME}" close >/dev/null 2>&1 || true
  echo "Session '${SESSION_NAME}' saved."
  exit 0
fi

if [[ -z "${PROJECT_URL}" ]]; then
  echo "Project URL is required. Pass --project-url or set TEST_PROJECT_URL." >&2
  exit 1
fi

echo "Running UI smoke against: ${PROJECT_URL}"
echo "Using persistent session: ${SESSION_NAME}"

playwright-cli "${OPEN_ARGS[@]}" >/dev/null
playwright-cli -s="${SESSION_NAME}" goto "${PROJECT_URL}" >/dev/null

title_out="$(playwright-cli -s="${SESSION_NAME}" eval "document.title" | tr -d '\r')"
signin_out="$(playwright-cli -s="${SESSION_NAME}" eval "document.body.innerText.includes('Sign in')" | tr -d '\r')"
phase_out="$(playwright-cli -s="${SESSION_NAME}" eval "document.body.innerText.includes('Phase')" | tr -d '\r')"
playwright-cli -s="${SESSION_NAME}" snapshot --filename="${SNAPSHOT_FILE}" >/dev/null || true
playwright-cli -s="${SESSION_NAME}" close >/dev/null 2>&1 || true

echo "Title check output:"
echo "${title_out}"
echo "Sign in check output:"
echo "${signin_out}"
echo "Phase text check output:"
echo "${phase_out}"
echo "Snapshot saved: ${SNAPSHOT_FILE}"

if echo "${signin_out}" | grep -q "true"; then
  echo "Not authenticated for project UI. Run '$0 --login --session ${SESSION_NAME}' first." >&2
  exit 2
fi

if ! echo "${phase_out}" | grep -q "true"; then
  echo "Authenticated but project page did not expose expected 'Phase' text." >&2
  exit 3
fi

echo "UI smoke passed."
