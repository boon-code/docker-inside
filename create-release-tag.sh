#!/bin/sh

_fail() {
    echo "ERROR: $@" >&2
    exit 1
}

_dbg() {
    echo "DEBUG: $@" >&2
}

version="$1"
[ -n "$version" ] || _fail "version not set"

echo "$version" | grep -E '^[0-9]+[.][0-9]+[.][0-9]+$'
[ $? -eq 0 ] || _fail "wrong versioning format"

[ -z "$(git tag -l "$version")" ] || _fail "Tag $version already exists"

tmp="$(grep -E '\s*__version__\s*=\s*"[0-9]+[.][0-9]+[.][0-9]+"' setup.py)"

[ "$(echo "$tmp" | wc -l)" -eq 1 ] || _fail "More then one line containing __version__ was found"

old="$(echo "$tmp" | sed -e 's/.*"\([0-9]\+[.][0-9]\+[.][0-9]\+\)".*/\1/')" || _fail "Failed to extract version"
_dbg "Found version in setup.py: $old"

[ "x$old" = "x$version" ] || _fail "Version mismatch: setup: ${old}, expected: $version"

git tag -s -a "$version"
