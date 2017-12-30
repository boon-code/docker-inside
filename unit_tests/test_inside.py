import os
import sys

import pytest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.realpath(os.path.join(THIS_DIR, '..'))
sys.path.insert(0, SRC_DIR)


@pytest.fixture()
def tapp():
    import dockerinside
    return dockerinside.DockerInsideApp(env={})


def test_argument_simple_parsing(tapp):
    simple_args = tapp._parseArgs(["ubuntu:latest"])
    assert simple_args.image == "ubuntu:latest"
    assert (not simple_args.volume)
    assert (not simple_args.mount_home)
    assert (not simple_args.name)


def test_argument_more_args(tapp):
    simple_args = tapp._parseArgs(
        ["--name=mycontainer",
         "-v", "/var/bla:/bla",
         "ubuntu:14.04"]
    )
    assert simple_args.image == "ubuntu:14.04"
    assert len(simple_args.volume) == 1
    assert simple_args.volume[0] == "/var/bla:/bla"
    assert (not simple_args.mount_home)
    assert simple_args.name == "mycontainer"


def test_simple_setup(tapp):
    tapp.run(['--auto-pull', 'ubuntu:16.04', 'echo "Hello, world"'])
