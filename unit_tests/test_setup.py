import os
import multiprocessing
import logging
import queue
import tempfile
import proxy
import pytest
from proxy.http.parser import HttpParser
from proxy.http.proxy import HttpProxyBasePlugin


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


@pytest.fixture()
def with_proxy(monkeypatch):
    ph = _ProxyHelper('127.0.0.1', 8899, monkeypatch)
    ph.drain_logged_requests()
    with proxy.Proxy(ph.proxy_args) as p:
        ph.proxy = p
        yield ph
    ph.drain_logged_requests()


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


def test_su_exec_setup_with_proxy(sapp, tmpdir, with_proxy):
    with_proxy.set_env()
    _test_su_exec_inner(sapp, tmpdir, ["--host-network"])
    # verify that proxy was used
    req = list(with_proxy.get_requests())
    _logger.info("setup issued %s requests to proxy", len(req))
    assert len(req) > 0


def test_basic_proxy_setup(with_proxy):
    """ Test case to ensure that proxy works as expected.

    This test case ensures that the proxy module works by ensuring that requests
    to the proxy are logged (using with_proxy fixture)
    """
    import requests
    requests.get("https://www.google.at")
    assert len(list(with_proxy.get_requests())) == 0, "Proxy has not been used"
    with_proxy.set_env()
    requests.get("https://www.google.at")
    r = list(with_proxy.get_requests())
    assert len(r) == 1, "Proxy has been used for request"
    with_proxy.drain_logged_requests()
    r = list(with_proxy.get_requests())
    assert len(r) == 0, "Proxy has been used for request"



class _ProxyHelper:

    def __init__(self, proxy_host, proxy_port, monkeypatch):
        self._host = proxy_host
        self._port = proxy_port
        self.proxy = None
        self._mp = monkeypatch

    def drain_logged_requests(self):
        # Discard and count discarded elements
        count = sum(1 for _ in self.get_requests())
        _logger.info("Discarded %s elements", count)

    def set_env(self):
        http_proxy = f"http://{self._host}:{self._port}"
        https_proxy = f"https://{self._host}:{self._port}"
        self._mp.setenv("http_proxy", http_proxy)
        self._mp.setenv("HTTP_PROXY", http_proxy)
        self._mp.setenv("https_proxy", https_proxy)
        self._mp.setenv("HTTPS_PROXY", https_proxy)

    @property
    def proxy_args(self):
        args = [f'--hostname={self._host}', f'--port={self._port}']
        args.extend([f'--plugins={__name__}.ListenProxyPlugin'])
        return args

    def get_requests(self, timeout=0.5):
        try:
            while True:
                yield ListenProxyPlugin.logged_requests.get(block=True, timeout=timeout)
        except queue.Empty:
            pass


class ListenProxyPlugin(HttpProxyBasePlugin):
    logged_requests = multiprocessing.Queue()

    def before_upstream_connection(self, request: HttpParser):
        return request

    def handle_client_request(self, request: HttpParser):
        self.logged_requests.put(request)
        return request

    def handle_upstream_chunk(self, chunk):
        return chunk

    def on_upstream_connection_close(self) -> None:
        pass