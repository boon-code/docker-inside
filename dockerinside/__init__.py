import os
import sys
import logging
import argparse
import argcomplete
import docker
import dockerpty

from . import dockerutils


class DockerInsideApp(dockerutils.BasicDockerApp):

    @classmethod
    def _parseArgs(cls, argv):
        parser = argparse.ArgumentParser()
        parser.add_argument('--verbose',
                            dest='verbosity',
                            action='store_const',
                            const=logging.DEBUG)
        parser.add_argument('--quiet',
                            dest='verbosity',
                            action='store_const',
                            const=logging.ERROR)
        parser.add_argument('--name',
                            help="Name of the container")
        parser.add_argument('-v', '--volume',
                            action="append",
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
        args = parser.parse_args(args=argv)
        return args

    def __init__(self, env=None):
        log = logging.getLogger("DockerInside")
        dockerutils.BasicDockerApp.__init__(self, log, env)
        self._args = None

    def _inside(self):
        """Run container with user environment"""
        self._assert_image_available(self._args.image, self._args.auto_pull)

    def run(self, argv):
        self._args = self._parseArgs(argv)
        try:
            self._inside()
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


def main():
    app = DockerInsideApp()
    app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
