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


# noinspection PyShadowingNames
def test_argument_simple_parsing(tapp):
    simple_args = tapp._parse_args(["ubuntu:latest"])
    assert simple_args.image == "ubuntu:latest"
    assert (not simple_args.volumes)
    assert (not simple_args.mount_home)
    assert (not simple_args.name)


# noinspection PyShadowingNames
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


def _filter_norm_text(txt):
    lines = txt.decode('utf-8').replace('\r','').split('\n')
    for line in lines:
        if line.startswith("DEBUG:"):
            sys.stderr.write(line + "\n")
        elif line == '':
            pass
        else:
            yield line


# noinspection PyShadowingNames
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
    assert 'Hello, world' == "\n".join(_filter_norm_text(txt))


# noinspection PyShadowingNames
@pytest.mark.parametrize("image", [
    'ubuntu:14.04', 'ubuntu:16.04', 'ubuntu:latest',
    'alpine:3.6', 'alpine:latest',
    'busybox:latest',
    'centos:latest',
    'fedora:latest',
])
def test_user_id_docker(tapp, image):
    args = ['--auto-pull', '--name=di_simple_setup_test',
            image, '--', 'id', "-u"]
    if os.environ.get("DIN_DEBUG_TEST", "") == "true":
        args.insert(0, '--debug')
        args.insert(0, '--verbose')
    txt = tapp.run(args, capture_stdout=True)
    assert "{0}".format(os.getuid()) == "\n".join(_filter_norm_text(txt))
