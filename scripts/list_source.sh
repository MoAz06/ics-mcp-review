#!/usr/bin/env bash
# List the source files of cloned repos, with the commit hash, for manual review.
# Usage: scripts/list_source.sh owner/name [owner/name ...]
cd "$(dirname "$0")/../data/src" || exit 1
for repo in "$@"; do
  d="${repo/\//__}"
  echo "== $repo $(git -C "$d" rev-parse --short HEAD) $(git -C "$d" ls-files | wc -l) files"
  git -C "$d" ls-files | grep -E '\.(py|ts|js|mjs|go|cs|rs|java|kt)$' | grep -viE '(^|/)(tests?|examples?|docs?|node_modules|dist|build)/' | head -40
done
