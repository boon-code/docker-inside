#!/bin/sh

if [ -z "${TRAVIS_TAG}" ]; then
    sed -i -e 's/\(__version__\s*=\s*"[^"]*\)"/\1.'"${TRAVIS_BUILD_NUMBER}"'"/g' setup.py
    version="$(egrep  '__version__.*"' setup.py | sed -e 's/.*"\([^"]\+\)"/\1/g')"
    echo "Building test version ${version}"
else
    echo "Building release ${TRAVIS_TAG}"
fi
