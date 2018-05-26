import os
import sys
import logging
import tempfile
import pytest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.realpath(os.path.join(THIS_DIR, '..'))
sys.path.insert(0, SRC_DIR)


def mock_basic_docker_app(env):
    from dockerinside.dockerutils import BasicDockerApp

    class MockBasicDockerApp(BasicDockerApp):
        def __init__(self):
            log = logging.getLogger("MockBasicDockerApp")
            BasicDockerApp.__init__(self, log, env)

    return MockBasicDockerApp()


@pytest.fixture()
def du():
    """dockerutils module"""
    from dockerinside import dockerutils
    return dockerutils


@pytest.fixture(scope='module')
def cert_mock_dir():
    td = tempfile.TemporaryDirectory(suffix='din-test')
    for i in ('cert.pem', 'key.pem', 'ca.pem'):
        with open(os.path.join(td.name, i), 'wb') as f:
            f.flush()
    sys.stderr.write("Created temporary directory: {0}\n".format(td.name))
    yield td.name
    sys.stderr.write("Clean-up directory: {0}\n".format(td.name))
    td.cleanup()


def test_split_and_filter(du):
    t1 = list(du._split_and_filter(["/", "/", "a", "b", "c", "/", "/"]))
    assert t1 == ["a", "b", "c"]
    t2 = list(du._split_and_filter(["a", "b", "c"]))
    assert t2 == ["a", "b", "c"]


def test_tmpfs_list(du):
    """Test --tmpfs parameter parsing"""
    exp1 = {"/dir1" : "rw,size=1G"}
    assert du.tmpfs_list_to_dict(["/dir1:rw,size=1G"]) == exp1
    exp2 = {"/dir1" : "", "/dir2" : "size=1G", "/dir3/bla" : "::::", "/dir4" : ""}
    assert du.tmpfs_list_to_dict(["/dir1", "/dir2:size=1G", "/dir3/bla:::::", "/dir4:"]) == exp2
