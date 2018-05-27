import os
import sys
import pwd
import grp
import logging
import argparse

import argcomplete
import docker
import docker.errors
import dockerpty

from . import dockerutils

_DEFAULT_LOG_FORMAT = "%(name)s : %(threadName)s : %(levelname)s : %(message)s"
logging.basicConfig(
    stream=sys.stderr,
    format=_DEFAULT_LOG_FORMAT,
    level=logging.INFO,
)

INSIDE_SCRIPT = b"""#!/bin/sh

BUSYBOX=0

_fail() {
    echo "ERROR: $@" >&2
    exit 1
}

_debug() {
    if [ "${DIN_VERBOSE}" = "1" ]; then
        echo "DEBUG: $@" >&2
    fi
}

_try_busybox_applets() {
    local applet=""

    if [ ! -e /bin/busybox ]; then
        _debug "busybox not found"
        return 1
    else
        _debug "busybox found - checking applets"
    fi

    for applet in "adduser" "addgroup"; do
        busybox --list | grep -F "${applet}" >/dev/null 2>/dev/null
        if [ $? -eq 0 ]; then
            _debug "found applet '${applet}'"
        else
            _debug "busybox is missing applet '${applet}'"
            return 1
        fi
    done

    _debug "All busybox applets found"

    return 0
}

_has_command() {
    local cmd="$1"
    local path=""

    path="$(command -v "${cmd}" 2>/dev/null)"
    if [ $? -ne 0 ] || [ -z "${path}" ]; then
        _debug "Command ${cmd} not found"
        return 1
    elif [ -L "${path}" ]; then  # centos...
        _debug "Command ${cmd} resolves to path ${path} which is a link"
        return 1
    else
        _debug "Resolved command ${cmd} to path ${path}"
        return 0
    fi
}

_add_group() {
    local grp_name="$1"
    local grp_id="$2"
    local ret=-1

    grep -E "^${grp_name}:" /etc/group >/dev/null 2>/dev/null
    if [ $? -ne 0 ]; then
        grep -E "^[^:]+:[^:]+:${grp_id}:" /etc/group >/dev/null 2>/dev/null
        if [ $? -ne 0 ]; then
            _debug "Create group ${grp_name} (${grp_id})"
            if [ ${BUSYBOX} -eq 1 ]; then
                /bin/busybox addgroup -g "${grp_id}" "${grp_name}" >/dev/null 2>/dev/null
                ret=$?
            elif _has_command "addgroup" ; then
                addgroup --gid "${grp_id}" "${grp_name}" >/dev/null 2>/dev/null
                ret=$?
            elif _has_command "groupadd" ; then
                groupadd --gid "${grp_id}" "${grp_name}" > /dev/null 2>/dev/null
                ret=$?
            else
                _fail "No command found to create a group"
            fi
            [ $ret -eq 0 ] || _fail "Couldn't create group '${grp_name}': errno=$ret"
            return 0
        else
            _debug "Group id ${grp_id} (${grp_name}) already used - skip"
            return 1
        fi
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

    if _try_busybox_applets ; then
        BUSYBOX=1
    fi

    _debug "BUSYBOX is ${BUSYBOX}"
    _debug "Current user: $(id -u)"

    _add_group "${DIN_GROUP}" "${DIN_GID}"

    _debug "Create user ${DIN_USER}"
    id -u ${DIN_USER} >/dev/null 2>/dev/null
    if [ $? -ne 0 ]; then
        local ret=-1
        if [ ${BUSYBOX} -eq 1 ]; then
            busybox adduser -G "${DIN_GROUP}" -u "${DIN_UID}" -s /bin/sh -D -H "${DIN_USER}" \
                    >/dev/null 2>/dev/null
            ret=$?
        elif _has_command "useradd" ; then
            useradd --gid "${DIN_GID}" \
                    --uid "${DIN_UID}" \
                    --shell /bin/sh \
                    --no-create-home \
                    --no-user-group \
                    "${DIN_USER}" >/dev/null 2>/dev/null
            ret=$?
        else
            _fail "No command found to add a user"
        fi
        [ $? -eq 0 ] || _fail "Couldn't create user ${DIN_USER}: errno=$?"
    else
        _debug "User '${DIN_USER}' already exists"
    fi

    for elm in ${DIN_GROUPS}; do
        local name="${elm%%,*}"
        local gid="${elm#*,}"

        if _add_group "${name}" "${gid}" ; then
            if [ ${BUSYBOX} -eq 1 ]; then
                busybox adduser "${DIN_USER}" "${name}" >/dev/null 2>/dev/null
                ret=$?
            elif _has_command "adduser" ; then
                adduser "${DIN_USER}" "${name}" >/dev/null 2>/dev/null
                ret=$?
            elif _has_command "usermod" ; then
                usermod --append --groups "${name}" "${DIN_USER}"
                ret=$?
            else
                _fail "No command found to add user to group"
            fi
            [ $? -eq 0 ] || _fail "Couldn't add user ${DIN_USER} to group ${name}"
        fi
    done

    _debug "Original entrypoint: ${DIN_ENTRYPOINT}"
    _debug "Inner command: $@"
    echo "#!/bin/sh" > /docker_inside_inner.sh
    echo "exec ${DIN_ENTRYPOINT} $@" >> /docker_inside_inner.sh
    chmod a+rx /docker_inside_inner.sh

    if [ "${DIN_CREATE_HOME}" = "1" ] && [ ! -d "/home/${DIN_USER}" ]; then
        _debug "Create temporary home directory: /home/${DIN_USER}"
        mkdir -p "/home/${DIN_USER}"
        chown "${DIN_USER}:${DIN_GROUP}" "/home/${DIN_USER}"
        chmod 0700 "/home/${DIN_USER}"
    fi

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
    X11_SOCKET = "/tmp/.X11-unix"

    @staticmethod
    def _add_docker_run_options(parser):
        parser.add_argument('--add-host',
                            help="Add a custom host-to-IP mapping (host:ip) (default [])")
        parser.add_argument('--cap-add',
                            action='append',
                            help="Add Linux capabilities (default [])")
        parser.add_argument('--cap-drop',
                            action='append',
                            help="Drop Linux capabilities (default [])")
        parser.add_argument('--device',
                            dest="devices",
                            action='append',
                            help="Add a host device to the container (default [])")
        parser.add_argument('-e', '--env',
                            action='append',
                            help="Set environment variables (default [])")
        parser.add_argument('-p', '--publish',
                            dest='ports',
                            action='append',
                            help="Publish a container's port(s) to the host ([ip:]hostp:contp)")
        parser.add_argument('--shm-size',
                            help="Size of /dev/shm, default value is 64MB")
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('-w', '--workdir',
                           help="Working directory inside the container")
        group.add_argument('-W', '--mount-workdir',
                           help="Mount and set working directory inside the container (volume spec)")
        parser.add_argument('--tmpfs',
                            dest='tmpfs',
                            action='append',
                            help="Mount tmpfs directories")

    @classmethod
    def _parse_args(cls, argv):
        parser = argparse.ArgumentParser()
        loglevel_group = parser.add_mutually_exclusive_group()
        loglevel_group.add_argument('--verbose',
                                    dest='loglevel',
                                    action='store_const',
                                    const=logging.DEBUG)
        loglevel_group.add_argument('--quiet',
                                    dest='loglevel',
                                    action='store_const',
                                    const=logging.ERROR)
        parser.add_argument('--debug',
                            action='store_true',
                            default=False,
                            help="Enable debug output in shell script")
        parser.add_argument('--init',
                            action='store_true',
                            default=False,
                            help="Use tini init process to forward signals and reap zombies")
        parser.add_argument('--gui',
                            action='store_true',
                            default=False,
                            help="Prepare settings for GUI applications (DISPLAY, X11)")
        parser.add_argument('--name',
                            help="Name of the container")
        parser.add_argument('-v', '--volume',
                            dest='volumes',
                            action="append",
                            default=[],
                            help="Bind mounts a volume")
        mnthome_grp = parser.add_mutually_exclusive_group()
        mnthome_grp.add_argument('-H', '--mount-home',
                                 action="store_true",
                                 default=False,
                                 help="Mount home directory")
        mnthome_grp.add_argument('--mount-as-home',
                                 help="Mount this directory as home")
        mnthome_grp.add_argument('--tmp-home',
                                 action='store_true',
                                 default=False,
                                 help="Create a temporary home directory")
        parser.add_argument('--auto-pull',
                            dest="auto_pull",
                            action="store_true",
                            default=False,
                            help="Pull unavailable images automatically")
        parser.add_argument('--switch-root',
                            action="store_true",
                            default=False,
                            help="Switch to root user during docker run")
        parser.add_argument('image',
                            help="The image to run")
        parser.add_argument('cmd',
                            nargs="?",
                            help="Command to be run")
        parser.add_argument('args',
                            nargs="*",
                            help="Arguments for command cmd")
        cls._add_docker_run_options(parser)
        parser.set_defaults(loglevel=logging.INFO)
        args = parser.parse_args(args=argv)
        return args

    def __init__(self, env=None):
        log = logging.getLogger("DockerInside")
        dockerutils.BasicDockerApp.__init__(self, log, env)
        self._args = None
        self._cobj = None

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
        env = dict()
        try:
            env.update(dockerutils.env_list_to_dict(image_info["Config"]["Env"]))
        except KeyError:
            self._log.exception("No key 'Env' in image info")
        env.update(dict(dockerutils.env_list_to_dict(self._args.env, self._env)))
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
        if self._args.gui:
            env["DISPLAY"] = os.environ.get("DISPLAY", '')
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
        if cmd is None:
            self._log.debug("command is null")
        else:
            self._log.debug("container command: {0}".format(" ".join(cmd)))
        return cmd

    def _inside(self):
        """Run container with user environment"""
        self._assert_image_available(self._args.image, self._args.auto_pull)
        image_info = self._dc.images.get(self._args.image).attrs
        pack_conf = {
            self.SCRIPT_NAME: {
                "payload": INSIDE_SCRIPT,
                "mode": 0o755,
            }
        }
        home_dir = os.path.expanduser('~')
        suexec = os.path.join(home_dir, '.config', 'docker_inside', 'su-exec')
        if os.path.exists(suexec):
            pack_conf.update({
                "/bin/su-exec": {
                    "file": suexec,
                    "mode": 0o755,
                }
            })
        script_pack = dockerutils.tar_pack(pack_conf)
        ports = dict(dockerutils.port_list_to_dict(self._args.ports))
        env = self._prepare_environment(image_info)
        cmd = self._prepare_command(image_info)
        volumes = self.volume_args_to_list(self._args.volumes)
        workdir = self._args.workdir
        if self._args.mount_workdir:
            wd_spec = dockerutils.normalize_volume_spec(self._args.mount_workdir)
            self._log.debug("Mount and set workdir {1} (volume spec: {0}:{1}:{2})".format(*wd_spec))
            volumes.append(dockerutils.volume_spec_to_string(wd_spec))
            workdir = wd_spec[1]
        if self._args.gui:
            if os.path.exists(self.X11_SOCKET):
                self._log.debug("Mount X11 unix socket")
                x11_spec = [self.X11_SOCKET, self.X11_SOCKET, 'rw']
                volumes.append(dockerutils.volume_spec_to_string(x11_spec))
        if self._args.mount_home:
            self._log.debug("Mount real home directory")
            mnt_spec = [home_dir, home_dir, 'rw']
            volumes.append(dockerutils.volume_spec_to_string(mnt_spec))
        elif self._args.mount_as_home is not None:
            self._log.debug("Mount fake home directory: {0}".format(self._args.mount_as_home))
            mnt_spec = [self._args.mount_as_home, home_dir, 'rw']
            volumes.append(dockerutils.volume_spec_to_string(mnt_spec))
        elif self._args.tmp_home:
            env['DIN_CREATE_HOME'] = "1"
        entrypoint = dockerutils.linux_pjoin('/', self.SCRIPT_NAME)
        self._log.debug("New entrypoint: {0}".format(entrypoint))
        creation_kwargs = dict(
            command=cmd,
            volumes=volumes,
            environment=env,
            entrypoint=entrypoint,
            name=self._args.name,
            cap_add=self._args.cap_add,
            cap_drop=self._args.cap_drop,
            devices=self._args.devices,
            ports=ports,
            working_dir=workdir,
            shm_size=self._args.shm_size,
            tty=True,
            stdin_open=True,
            init=self._args.init,
        )
        if self._args.switch_root:
            creation_kwargs['user'] = "0"
        if self._args.tmpfs:
            creation_kwargs['tmpfs'] = dockerutils.tmpfs_list_to_dict(self._args.tmpfs)
        self._cobj = self._dc.containers.create(self._args.image, **creation_kwargs)
        self._cobj.put_archive('/', script_pack)
        self._start()

    @staticmethod
    def _isatty():
        return os.isatty(sys.stdin.fileno())

    def _start(self):
        self._log.info("Starting container: {0}".format(self._cobj.id))
        if self._isatty():
            dockerpty.start(self._dc.api, self._cobj.id)
        else:
            self._cobj.start()
        self._cobj.wait()
        self._log.info("Container {0} stopped".format(self._cobj.id))

    def cleanup(self):
        if self._cobj is None:
            self._log.debug("'Inside' containter has already been deleted")
            return
        self._cobj.stop()
        self._cobj.remove()
        self._cobj = None

    def run(self, argv, capture_stdout=False):
        self._args = self._parse_args(argv)
        self._adapt_log_level()
        try:
            self._inside()
            if capture_stdout:
                return self._cobj.logs(stderr=False)
        except dockerutils.InvalidPath as e:
            logging.exception("{0} '{1}' doesn't exist".format(e.type_, e.path))
        except docker.errors.ImageNotFound:
            if self._args.auto_pull:
                logging.exception("Image not found locally: try pulling the image before?")
            else:
                logging.exception("Image not found")
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
