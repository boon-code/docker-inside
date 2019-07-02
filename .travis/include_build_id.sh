#!/bin/sh

_get_version() {
    egrep  '__version__.*"' setup.py | sed -e 's/.*"\([^"]\+\)"/\1/g'
}

if [ -z "${TRAVIS_TAG}" ]; then
    sed -i -e 's/\(__version__\s*=\s*"[^"]*\)"/\1.'"${TRAVIS_BUILD_NUMBER}"'"/g' setup.py
    version="$(_get_version)"
    echo "Building test version ${version}"
else
    version="$(_get_version)"
    if [ "$version" = "${TRAVIS_TAG}" ]; then
        echo "Building release ${TRAVIS_TAG}"
    else
        echo "ERROR: tag and version don't match: tag='${TRAVIS_TAG}', version='$version'"
        exit 1
    fi
fi
