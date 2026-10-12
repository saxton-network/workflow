#!/usr/bin/env bash
# Accept only v-prefixed SemVer 2.0.0 release tags (no build metadata).
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <version-tag>" >&2
  exit 2
fi

num='(0|[1-9][0-9]*)'
ident='(0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
pattern="^v${num}\.${num}\.${num}(-${ident}(\.${ident})*)?$"

if [[ ! "$1" =~ $pattern ]]; then
  echo "Invalid version tag: $1 (expected vMAJOR.MINOR.PATCH[-PRERELEASE])" >&2
  exit 1
fi
