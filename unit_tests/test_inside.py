import os
import sys

import pytest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.realpath(os.path.join(THIS_DIR, '..'))
sys.path.insert(0, SRC_DIR)


@pytest.fixture()
def tapp():
    import dockerinside
    app = dockerinside.DockerInsideApp(env={})
    app._isatty = lambda: False
    return app


def test_argument_simple_parsing(tapp):
    simple_args = tapp._parse_args(["ubuntu:latest"])
    assert simple_args.image == "ubuntu:latest"
    assert (not simple_args.volumes)
    assert (not simple_args.mount_home)
    assert (not simple_args.name)


def test_argument_more_args(tapp):
    simple_args = tapp._parse_args(
        ["--name=mycontainer",
         "-v", "/var/bla:/bla",
         "ubuntu:14.04"]
    )
    assert simple_args.image == "ubuntu:14.04"
    assert len(simple_args.volumes) == 1
    assert simple_args.volumes[0] == "/var/bla:/bla"
    assert (not simple_args.mount_home)
    assert simple_args.name == "mycontainer"


def test_simple_setup_docker(tapp):
    txt = tapp.run(
        ['--auto-pull',
         '-e', "TEXT=Hello, world",
         '--name=di_simple_setup_test',
         'ubuntu:16.04',
         'echo',
         "${TEXT}"],
        capture_stdout=True
    )
    assert b'Hello, world\r\n' == txt


@pytest.mark.parametrize("image", [
    'ubuntu:14.04', 'ubuntu:16.04', 'ubuntu:latest',
    'alpine:3.6', 'alpine:latest',
    'busybox:latest'
])
def test_user_id_docker(tapp, image):
    txt = tapp.run(
        ['--auto-pull',
         '--name=di_simple_setup_test',
         image,
         '--',
         'id',
         "-u"],
        capture_stdout=True
    )
    assert "{0}\r\n".format(os.getuid()) == txt.decode('utf-8')
