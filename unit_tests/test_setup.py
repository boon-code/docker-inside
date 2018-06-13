import os
import sys
import tempfile
import pytest


@pytest.fixture()
def sapp():
    import dockerinside.setup as din_setup
    setup_app = din_setup.SetupApp(env={})
    setup_app._isatty = lambda: False
    return setup_app


@pytest.fixture()
def tmpdir():
    td = tempfile.TemporaryDirectory(suffix='din-setup-test')
    sys.stderr.write("Create temporary directory: {0}\n".format(td.name))
    yield td.name
    sys.stderr.write("Delete temporary directory: {0}\n".format(td.name))
    td.cleanup()


def test_su_exec_setup(sapp, tmpdir):
    sapp.run([
        "--name", "setup-test",
        "--home", tmpdir,
        "--auto-pull",
    ])
    su_exec = os.path.join(tmpdir, ".config", "docker_inside", "su-exec")
    assert os.path.isfile(su_exec)
