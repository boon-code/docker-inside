import os
import sys
import argparse
import logging

import docker
import docker.errors
import dockerpty

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
        os.makedirs(cfg_path, 0o755, exist_ok=True)
        script_pack = dockerutils.tar_pack({
            "entrypoint.sh": {
                "payload": SETUP_SCRPT,
                "mode": 0o755,
            }
        })
        volumes = self.volume_args_to_dict([
            "{0}:/din_config".format(cfg_path)
        ])
        env = {
            "DIN_UID": os.getuid(),
            "DIN_GID": os.getgid(),
            "DIN_SU_EXEC_URL": url,
            "DIN_REFSPEC": refspec,
        }
        cobj = self._dc.containers.create(
            self.DEFAULT_IMAGE,
            command="/entrypoint.sh",
            volumes=volumes,
            environment=env,
            name=name,
        )
        try:
            cobj.put_archive('/', script_pack)
            dockerpty.start(self._dc.api, cobj.id)
            cobj.wait()
        finally:
            cobj.stop()
            cobj.remove()

    def run(self, argv):
        self._args = self._parse_args(argv)
        logging.getLogger().setLevel(self._args.loglevel)
        try:
            self.setup(self._args.url,
                       home=self._args.home,
                       auto_pull=self._args.auto_pull,
                       name=self._args.name,
                       refspec=self._args.refspec)
        except dockerutils.InvalidPath as e:
            logging.exception("{0} '{1}' doesn't exist".format(e.type_, e.path))
        except docker.errors.ImageNotFound:
            logging.exception("Image '{0}' not found".format(self.DEFAULT_IMAGE))
        except Exception:
            logging.exception("Failed to run setup()")


def setup_main():
    app = SetupApp()
    app.run(sys.argv[1:])
