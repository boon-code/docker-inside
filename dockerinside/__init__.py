import os
import sys
import pwd
import grp
import logging
import argparse

import argcomplete
import dockerpty

from . import dockerutils

_DEFAULT_LOG_FORMAT = "%(name)s : %(threadName)s : %(levelname)s : %(message)s"
logging.basicConfig(
    stream=sys.stderr,
    format=_DEFAULT_LOG_FORMAT,
    level=logging.INFO,
)

INSIDE_SCRIPT = b"""#!/bin/sh

if [ -e /bin/busybox ]; then
    BUSYBOX=1
else
    BUSYBOX=0
fi

_fail() {
    echo "ERROR: $@" >&2
    exit 1
}

_debug() {
    if [ "${DIN_VERBOSE}" = "1" ]; then
        echo "DEBUG: $@" >&2
    fi
}

_add_group() {
    local grp_name="$1"
    local grp_id="$2"
    local ret=-1

    grep -E "^${grp_name}:" /etc/group >/dev/null 2>/dev/null
    if [ $? -ne 0 ]; then
        _debug "Create group ${grp_name} (${grp_id})"
        if [ ${BUSYBOX} -eq 1 ]; then
            /bin/busybox addgroup -g "${grp_id}" "${grp_name}" >/dev/null 2>/dev/null
            ret=$?
        else
            addgroup --gid "${grp_id}" "${grp_name}" >/dev/null 2>/dev/null
            ret=$?
        fi
        [ $ret -eq 0 ] || _fail "Couldn't create group '${grp_name}': errno=$ret"
    else
        _debug "Group '${grp_name}' already exists"
    fi
}

try_su_exec() {
    local tmp=""

    if [ -e /bin/su-exec ]; then
        _debug "su-exec binary found"
    else
        _debug "su-exec binary not found"
        return 1
    fi

    tmp="$(/bin/su-exec "${DIN_USER}" id -u)"
    if [ "${tmp}" = "${DIN_UID}" ]; then
        _debug "su-exec seems to work: uid=${tmp}"
        return 0
    else
        _debug "su-exec call failed: uid=${tmp}"
        return 1
    fi
}

main() {

    if [ "${DIN_VERBOSE}" = "1" ]; then
        echo ""
    fi

    _add_group "${DIN_GROUP}" "${DIN_GID}"

    _debug "Create user ${DIN_USER}"
    id -u ${DIN_USER} >/dev/null 2>/dev/null
    if [ $? -ne 0 ]; then
        local ret=-1
        if [ ${BUSYBOX} -eq 1 ]; then
            /bin/busybox adduser -G "${DIN_GROUP}" -u "${DIN_UID}" -s /bin/sh -D -H "${DIN_USER}" >/dev/null 2>/dev/null
            ret=$?
        else
            useradd --gid "${DIN_GID}" \
                    --uid "${DIN_UID}" \
                    --shell /bin/sh \
                    --no-create-home \
                    --no-user-group \
                    "${DIN_USER}" >/dev/null 2>/dev/null
            ret=$?
        fi
        [ $? -eq 0 ] || _fail "Couldn't create user ${DIN_USER}: errno=$?"
    else
        _debug "User '${DIN_USER}' already exists"
    fi

    for elm in ${DIN_GROUPS}; do
        local name="${elm%%,*}"
        local gid="${elm#*,}"

        _add_group "${name}" "${gid}"
        adduser "${DIN_USER}" "${name}" >/dev/null 2>/dev/null
        [ $? -eq 0 ] || _fail "Couldn't add user ${DIN_USER} to group ${name}"
    done

    _debug "Original entrypoint: ${DIN_ENTRYPOINT}"
    _debug "Inner command: $@"
    echo "exec ${DIN_ENTRYPOINT} $@" > /docker_inside_inner.sh
    chmod a+rx /docker_inside_inner.sh

    if try_su_exec ; then
        exec su-exec "${DIN_USER}" "/docker_inside_inner.sh"
    else
        exec su -c "/docker_inside_inner.sh" "${DIN_USER}"
    fi
}

main $@
"""


class DockerInsideApp(dockerutils.BasicDockerApp):
    SCRIPT_NAME = "docker_inside.sh"

    @classmethod
    def _parseArgs(cls, argv):
        parser = argparse.ArgumentParser()
        parser.add_argument('--verbose',
                            dest='loglevel',
                            action='store_const',
                            const=logging.DEBUG)
        parser.add_argument('--quiet',
                            dest='loglevel',
                            action='store_const',
                            const=logging.ERROR)
        parser.add_argument('--debug',
                            action='store_true',
                            default=False,
                            help="Enable debug output in shell script")
        parser.add_argument('--name',
                            help="Name of the container")
        parser.add_argument('-v', '--volume',
                            dest='volumes',
                            action="append",
                            default=[],
                            help="Bind mounts a volume")
        parser.add_argument('-H', '--mount-home',
                            action="store_true",
                            default=False,
                            help="Mount home directory")
        parser.add_argument('--auto-pull',
                            dest="auto_pull",
                            action="store_true",
                            default=False,
                            help="Pull unavailable images automatically")
        parser.add_argument('image',
                            help="The image to run")
        parser.add_argument('cmd',
                            nargs="?",
                            help="Command to be run")
        parser.add_argument('args',
                            nargs="*",
                            help="Arguments for command cmd")
        parser.set_defaults(loglevel=logging.INFO)
        args = parser.parse_args(args=argv)
        return args

    def __init__(self, env=None):
        log = logging.getLogger("DockerInside")
        dockerutils.BasicDockerApp.__init__(self, log, env)
        self._args = None
        self._cid = None

    def _adapt_log_level(self):
        if not self._args.debug:
            logging.getLogger('urllib3').setLevel(logging.INFO)
        logging.getLogger().setLevel(self._args.loglevel)

    def _prepare_environment(self, image_info):
        uid = os.getuid()
        gid = os.getgid()
        username = pwd.getpwuid(uid).pw_name
        groupname = grp.getgrgid(gid).gr_name
        groups = dockerutils.get_user_groups(username)
        self._log.debug("User account {0} ({1})".format(username, uid))
        self._log.debug("Main group {0} ({1})".format(groupname, gid))
        groups_txt = ",".join([i.gr_name for i in groups])
        group_env = "\n".join(["{0},{1}".format(i.gr_name, i.gr_gid) for i in groups])
        self._log.debug("All groups: {0}".format(groups_txt))
        try:
            env = dict(dockerutils.env_list_to_dict(image_info["Config"]["Env"]))
            if env is None:
                self._log.debug("Empty environment")
                env = {}
        except KeyError:
            self._log.exception("No key 'Env' in image info")
            env = {}
        env.update({
            "DIN_UID": uid,
            "DIN_USER": username,
            "DIN_GID": gid,
            "DIN_GROUP": groupname,
            "DIN_GROUPS": group_env,
            "DIN_GROUP_NAMES": groups_txt,
        })
        if self._args.debug:
            env["DIN_VERBOSE"] = "1"
        try:
            last_ep = image_info["Config"]["Entrypoint"]
            if last_ep is not None:
                env["DIN_ENTRYPOINT"] = last_ep
                self._log.debug("Old entrypoint: {0}".format(last_ep))
            else:
                self._log.debug("Old entrypoint wasn't set (null)")
        except KeyError:
            self._log.exception("No 'Entrypoint' in image info")
        return env

    def _prepare_command(self, image_info):
        try:
            cmd = image_info["Config"]["Cmd"]
        except KeyError:
            cmd = None
        if self._args.cmd:
            cmd = [self._args.cmd]
            cmd.extend(self._args.args)
        self._log.debug("container command: {0}".format(" ".join(cmd)))
        return cmd

    def _inside(self):
        """Run container with user environment"""
        self._assert_image_available(self._args.image, self._args.auto_pull)
        image_info = self._dc.inspect_image(self._args.image)
        pack_conf = {
            self.SCRIPT_NAME: {
                "payload": INSIDE_SCRIPT,
                "mode": 0o755,
            }
        }
        suexec = os.path.join(os.path.expanduser('~'), '.config', 'docker_inside', 'su-exec')
        if os.path.exists(suexec):
            pack_conf.update({
                "/bin/su-exec": {
                    "file": suexec,
                    "mode": 0o755,
                }
            })
        script_pack = dockerutils.tar_pack(pack_conf)
        hostcfg = self._dc.create_host_config(
            binds=self.volume_args_to_dict(self._args.volumes)
        )
        env = self._prepare_environment(image_info)
        cmd = self._prepare_command(image_info)
        entrypoint = dockerutils.linux_pjoin('/', self.SCRIPT_NAME)
        self._log.debug("New entrypoint: {0}".format(entrypoint))
        self._cid = self._dc.create_container(
            self._args.image,
            command=cmd,
            host_config=hostcfg,
            environment=env,
            entrypoint=entrypoint,
            name=self._args.name,
            tty=True,
            stdin_open=True,
        )
        self._dc.put_archive(self._cid, '/', script_pack)
        self._start()

    def _isatty(self):
        return os.isatty(sys.stdin.fileno())

    def _start(self):
        self._log.info("Starting container: {0}".format(self._cid['Id']))
        if self._isatty():
            dockerpty.start(self._dc, self._cid['Id'])
        else:
            self._dc.start(self._cid)
        self._dc.wait(self._cid)
        self._log.info("Container {0} stopped".format(self._cid['Id']))

    def cleanup(self):
        if self._cid is None:
            self._log.debug("'Inside' containter has already been deleted")
            return
        self._dc.stop(self._cid)
        self._dc.remove_container(self._cid)
        self._cid = None

    def run(self, argv, capture_stdout=False):
        self._args = self._parseArgs(argv)
        self._adapt_log_level()
        try:
            self._inside()
            if capture_stdout:
                return self._dc.logs(self._cid, stderr=False)
        except dockerutils.InvalidPath as e:
            logging.exception("{0} '{1}' doesn't exist".format(e.type_, e.path))
        except dockerutils.MissingImageError as e:
            if not e.pull:
                logging.exception(
                    "Missing image {0}: try pulling the image before?".format(e.fullname)
                )
            else:
                logging.exception("Image {0} doesn't exist".format(e.fullname))
        except Exception:
            logging.exception("Failed to run inside()")
        finally:
            self.cleanup()
        return None


def main():
    app = DockerInsideApp()
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()