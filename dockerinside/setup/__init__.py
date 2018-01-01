import os
import sys
import argparse
import logging

import dockerpty

from .. import dockerutils

_DEFAULT_LOG_FORMAT = "%(name)s : %(threadName)s : %(levelname)s : %(message)s"
logging.basicConfig(
    stream=sys.stderr,
    format=_DEFAULT_LOG_FORMAT,
    level=logging.INFO,
)

SETUP_SCRPT = b"""#!/bin/bash

set -e
DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential git-core

cd /tmp
git clone -b "${DIN_REFSPEC}" "${DIN_SU_EXEC_URL}" su-exec
cd su-exec

gcc -static su-exec.c -o su-exec
cp -v su-exec /din_config/
chown "${DIN_UID}:${DIN_GID}" /din_config/su-exec
"""


class SetupApp(dockerutils.BasicDockerApp):
    DEFAULT_SU_EXEC_URL = "https://github.com/ncopa/su-exec.git"
    DEFAULT_IMAGE = "ubuntu:16.04"

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
        dockerutils.BasicDockerApp.__init__(self, log, env)

    def setup(self, url, home=None, auto_pull=False, name=None, refspec=None):
        if home is None:
            home = os.path.expanduser('~')
        if refspec is None:
            refspec = 'master'
        self._assert_image_available(self.DEFAULT_IMAGE, auto_pull)
        cfg_path = os.path.join(home, '.config', 'docker_inside')
        os.makedirs(cfg_path, 0o755, exist_ok=True)
        script_pack = dockerutils.tar_pack({
            "entrypoint.bash": {
                "payload": SETUP_SCRPT,
                "mode": 0o755,
            }
        })
        hostcfg = self._dc.create_host_config(
            binds=self.volume_args_to_dict([
                "{0}:/din_config".format(cfg_path)
            ])
        )
        env = {
            "DIN_UID": os.getuid(),
            "DIN_GID": os.getgid(),
            "DIN_SU_EXEC_URL": url,
            "DIN_REFSPEC": refspec,
        }
        cid = self._dc.create_container(
            self.DEFAULT_IMAGE,
            command="/entrypoint.bash",
            host_config=hostcfg,
            environment=env,
            name=name,
        )
        try:
            self._dc.put_archive(cid, '/', script_pack)
            dockerpty.start(self._dc, cid['Id'])
            self._dc.wait(cid)
        finally:
            self._dc.stop(cid)
            self._dc.remove_container(cid)

    def run(self, argv):
        self._args = self._parse_args(argv)
        logging.getLogger().setLevel(self._args.loglevel)
        try:
            self.setup(self._args.url,
                       auto_pull=self._args.auto_pull,
                       name=self._args.name)
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
            logging.exception("Failed to run setup()")


def setup_main():
    app = SetupApp()
    app.run(sys.argv[1:])
