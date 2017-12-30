import os
import sys
import logging
import tempfile
import pytest
import docker
import docker.tls

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.realpath(os.path.join(THIS_DIR, '..'))
sys.path.insert(0, SRC_DIR)


def mock_basic_docker_app(env):
    from dockerinside.dockerutils import BasicDockerApp

    class MockBasicDockerApp(BasicDockerApp):
        @classmethod
        def _create_docker_client(cls, params):
            return None

        def __init__(self):
            log = logging.getLogger("MockBasicDockerApp")
            BasicDockerApp.__init__(self, log, env)

    return MockBasicDockerApp()


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


# noinspection PyShadowingNames
def test_get_client_config_with_env(cert_mock_dir):
    env = {
        'DOCKER_TLS_VERIFY': "1",
        'DOCKER_HOST': "localhost",
        'DOCKER_CERT_PATH': cert_mock_dir,
    }
    dut = mock_basic_docker_app(env)
    ret, params = dut._get_client_config(env)
    assert ret, "All settings must be passed"
    assert params['base_url'] == "localhost"
    assert isinstance(params['tls'], docker.tls.TLSConfig)


# noinspection PyShadowingNames
def test_get_client_config_with_incomplete_env(cert_mock_dir):
    env = {
        'DOCKER_HOST': "localhost",
        'DOCKER_CERT_PATH': cert_mock_dir,
    }
    dut = mock_basic_docker_app(env)
    ret, params = dut._get_client_config(env)
    assert not ret, "Default settings with local docker client"
    assert ('base_url', 'tls') not in params.keys()


def test_get_client_config_without_env():
    env = {}
    dut = mock_basic_docker_app(env)
    ret, params = dut._get_client_config(env)
    assert not ret, "Default settings with local docker client"
    assert ('base_url', 'tls') not in params.keys()


def test_split_and_filter():
    from dockerinside import dockerutils as du
    t1 = list(du._split_and_filter(["/", "/", "a", "b", "c", "/", "/"]))
    assert t1 == ["a", "b", "c"]
    t2 = list(du._split_and_filter(["a", "b", "c"]))
    assert t2 == ["a", "b", "c"]
