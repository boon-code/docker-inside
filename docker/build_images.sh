#!/bin/sh

_find_free_id() {
    local gid_or_uid="$1"
    local cid=$2
    local ret=-1

    while [ true ]; do
        if [ "${gid_or_uid}" = "uid" ]; then
            grep -E "^[^:]+:[^:]+:${cid}[:].*" /etc/passwd 2>/dev/null 1>/dev/null
            ret=$?
        elif [ "${gid_or_uid}" = "gid" ]; then
            grep -E "^[^:]+:[^:]+:${cid}:.*" /etc/group 2>/dev/null 1>/dev/null
            ret=$?
        else
            echo "set gid_or_uid to either 'uid' or 'gid"
            return 1
        fi

        if [ $ret -ne 0 ]; then
            echo "$cid"
            return 0
        fi
        cid=$(( cid + 1 ))
    done
}


main() {
    local tpldir="$1"
    local uname="$(id -u -n)"
    local gname="$(id -g -n)"
    local uid="$(id -u)"
    local gid="$(id -g)"
    local extuid="$(_find_free_id "uid" ${uid})"
    local extgid="$(_find_free_id "gid" ${gid})"
    local path=""

    [ -n "$tpldir" ] || exit 1

    find "$tpldir" -name "Dockerfile.tpl" | while read path; do
        local dir="$(dirname "$path")"
        local name="$(basename "$dir")"

        echo "Base: $name"
        sed -e "s/@@USER@@/$uname/g" -e "s/@@UID@@/$uid/g" -e "s/@@GID@@/$gid/g" \
            -e "s/@@EXTUSER@@/extrauser/g" -e "s/@@EXTUID@@/$extuid/g" -e "s/@@EXTGID@@/$extgid/g" \
            "${path}" > "${dir}/Dockerfile"

        docker build --no-cache -t "dintest/${name}:latest" "${dir}"
    done
}

main "$@"
