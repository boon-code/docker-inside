import os
import sys
import errno
import argparse
import logging

import docker
import docker.errors

from .. import dockerutils

_DEFAULT_LOG_FORMAT = "%(name)s : %(threadName)s : %(levelname)s : %(message)s"
logging.basicConfig(
    stream=sys.stderr,
    format=_DEFAULT_LOG_FORMAT,
    level=logging.INFO,
)

SETUP_SCRPT = b"""#!/bin/sh

set -e
apk add --no-cache git musl-dev gcc

cd /tmp
git clone -b "${DIN_REFSPEC}" "${DIN_SU_EXEC_URL}" su-exec
cd su-exec

gcc -static su-exec.c -o su-exec
cp -v su-exec /din_config/
chown "${DIN_UID}:${DIN_GID}" /din_config/su-exec
"""


class SetupApp(dockerutils.BasicDockerApp):
    DEFAULT_SU_EXEC_URL = "https://github.com/ncopa/su-exec.git"
    DEFAULT_IMAGE = "alpine:3.6"
    PASSED_HOST_ENV = (
        'https_proxy', 'http_proxy',
        'HTTPS_PROXY', 'HTTP_PROXY',
        'HTTP_PROXY_AUTH'
    )

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
        parser.add_argument('--url',
                            default=cls.DEFAULT_SU_EXEC_URL,
                            help="Git URL to su-exec repository")
        parser.add_argument('--name',
                            help="Name of the container")
        parser.add_argument('--home',
                            help="Override path to home directory")
        parser.add_argument('--auto-pull',
                            dest="auto_pull",
                            action="store_true",
                            default=False,
                            help="Pull unavailable images automatically")
        parser.add_argument('--refspec',
                            help="Refspec for su-exec repo (tag/branch; default: master)")
        parser.add_argument('--host-network',
                            action="store_true",
                            default=False,
                            help="Allow access to host network (f.e. if using a proxy on locahost)")
        parser.set_defaults(loglevel=logging.INFO)
        args = parser.parse_args(args=argv)
        return args

    def __init__(self, env=None):
        log = logging.getLogger("DockerInside.Setup")
        self._args = None
        dockerutils.BasicDockerApp.__init__(self, log, env)

    def setup(self, url, home=None, auto_pull=False, name=None, refspec=None):
        if home is None:
            home = os.path.expanduser('~')
        if refspec is None:
            refspec = 'master'
        self._assert_image_available(self.DEFAULT_IMAGE, auto_pull)
        cfg_path = os.path.join(home, '.config', 'docker_inside')
        self._log.debug("Configuration directory (host): {0}".format(cfg_path))
        try:
            os.makedirs(cfg_path, 0o755)
        except OSError as e:
            if (e.errno == errno.EEXIST) and os.path.isdir(cfg_path):
                logging.debug("Directory '{0}' already exists".format(cfg_path))
            else:
                raise
        script_pack = dockerutils.tar_pack({
            "entrypoint.sh": {
                "payload": SETUP_SCRPT,
                "mode": 0o755,
            }
        })
        volumes = self.volume_args_to_list([
            "{0}:/din_config".format(cfg_path)
        ])
        env = {
            "DIN_UID": os.getuid(),
            "DIN_GID": os.getgid(),
            "DIN_SU_EXEC_URL": url,
            "DIN_REFSPEC": refspec,
        }
        host_env = dict({k:v for k,v in os.environ.items() if k in self.PASSED_HOST_ENV})
        env.update(host_env)
        logging.debug("Prepared environment: %s", host_env)
        network_mode = 'host' if self._args.host_network else None
        logging.debug("Network mode: %s", "default" if network_mode is None else network_mode)
        cobj = self._dc.containers.create(
            self.DEFAULT_IMAGE,
            command="/entrypoint.sh",
            volumes=volumes,
            environment=env,
            name=name,
            network=network_mode
        )
        try:
            cobj.put_archive('/', script_pack)
            cobj.start()
            for msg in cobj.logs(stdout=True, stderr=True, stream=True):
                logging.debug("{0}".format(msg.decode('utf-8').rstrip('\n')))
            ret = cobj.wait()
            status_code = ret.get('StatusCode', None)
            logging.info("setup returned %s", status_code)
            return status_code
        finally:
            cobj.stop()
            cobj.remove()

    def run(self, argv):
        ret = 1
        self._args = self._parse_args(argv)
        logging.getLogger().setLevel(self._args.loglevel)
        # noinspection PyBroadException
        try:
            ret = self.setup(
                self._args.url,
                home=self._args.home,
                auto_pull=self._args.auto_pull,
                name=self._args.name,
                refspec=self._args.refspec
            )
        except dockerutils.InvalidPath as e:
            logging.exception("{0} '{1}' doesn't exist".format(e.type_, e.path))
        except docker.errors.ImageNotFound:
            logging.exception("Image '{0}' not found".format(self.DEFAULT_IMAGE))
        except Exception:
            logging.exception("Failed to run setup()")
        finally:
            return ret


def setup_main():
    app = SetupApp()
    app.run(sys.argv[1:])
