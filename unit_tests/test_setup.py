import os
import logging
import tempfile
import pytest


_logger = logging.getLogger(__name__)


@pytest.fixture()
def sapp():
    import dockerinside.setup as din_setup
    setup_app = din_setup.SetupApp(env={})
    setup_app._isatty = lambda: False
    return setup_app


@pytest.fixture()
def tmpdir():
    td = tempfile.TemporaryDirectory(suffix='din-setup-test')
    _logger.info("Create temporary directory: %s", td.name)
    yield td.name
    _logger.info(f"Delete temporary directory: %s", td.name)
    td.cleanup()


def _test_su_exec_inner(sapp, tmpdir, extra_args=[]):
    su_exec = os.path.join(tmpdir, ".config", "docker_inside", "su-exec")
    args = [
        "--name", "setup-test",
        "--home", tmpdir,
        "--auto-pull",
    ]
    args.extend(extra_args)
    assert not os.path.isfile(su_exec), "su-exec binary must not exist prio to the test"
    assert sapp.run(args) == 0, "Command is expected to succeed (return 0)"
    assert os.path.isfile(su_exec), "su-exec binary has to exist"


@pytest.mark.parametrize('extra_args', [
    [],
    ['--host-network']
])
def test_su_exec_setup(sapp, tmpdir, extra_args):
    _test_su_exec_inner(sapp, tmpdir, extra_args)

