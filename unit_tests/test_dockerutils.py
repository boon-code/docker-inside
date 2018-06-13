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


# noinspection PyShadowingNames
def test_split_and_filter(du):
    t1 = list(du._split_and_filter(["/", "/", "a", "b", "c", "/", "/"]))
    assert t1 == ["a", "b", "c"]
    t2 = list(du._split_and_filter(["a", "b", "c"]))
    assert t2 == ["a", "b", "c"]


# noinspection PyShadowingNames
def test_tmpfs_list(du):
    """Test --tmpfs parameter parsing"""
    exp1 = {"/dir1": "rw,size=1G"}
    assert du.tmpfs_list_to_dict(["/dir1:rw,size=1G"]) == exp1
    exp2 = {"/dir1": "", "/dir2": "size=1G", "/dir3/bla": "::::", "/dir4": ""}
    assert du.tmpfs_list_to_dict(["/dir1", "/dir2:size=1G", "/dir3/bla:::::", "/dir4:"]) == exp2


# noinspection PyShadowingNames
def test_assert_path_exists(du):
    p_file = os.path.abspath(__file__)
    p_dir = os.path.dirname(__file__)
    p_invalid_path = p_file + "thisfiledoesnotexistandwillnever"
    with pytest.raises(du.InvalidPath):
        du._assert_path_exists(p_file, 'directory')
    with pytest.raises(du.InvalidPath):
        du._assert_path_exists(p_dir, 'file')
    with pytest.raises(du.InvalidPath):
        du._assert_path_exists(p_invalid_path, 'file')
    with pytest.raises(du.InvalidPath):
        du._assert_path_exists(p_invalid_path, 'directory')
    with pytest.raises(du.InvalidPath):
        du._assert_path_exists(p_invalid_path)
    du._assert_path_exists(p_file)
    du._assert_path_exists(p_dir)
    du._assert_path_exists(p_file, 'file')
    du._assert_path_exists(p_dir, 'directory')


# noinspection PyShadowingNames
def test_env_list_to_dict(monkeypatch, du):
    host_env = dict(T1="Text1", T2="Text2")
    args_env = ["T3=Text3", "VAR4=Text4", "T2=Different"]
    with monkeypatch.context() as m:
        m.setattr(os, 'environ', host_env)
        env = dict(du.env_list_to_dict(args_env))
        assert env == {
            "T2": "Different",
            "T3": "Text3",
            "VAR4": "Text4"
        }
    env = dict(du.env_list_to_dict(args_env, host_env))
    assert env == {
        "T2": "Different",
        "T3": "Text3",
        "VAR4": "Text4"
    }
    assert dict(du.env_list_to_dict([], host_env)) == {}


# noinspection PyShadowingNames
def test_ports_normalization(du):
    assert du.split_port_normalized("9000/udp") == (9000, 'udp')
    assert du.split_port_normalized("9001") == (9001, 'tcp')
    assert du.split_port_normalized("9002/tcp") == (9002, 'tcp')
    assert du.normalize_port("9000") == "9000/tcp"
    assert du.normalize_port("9001/udp") == "9001/udp"
    assert du.normalize_port("9002/tcp") == "9002/tcp"
    ports = dict(du.port_list_to_dict([
        "1.2.3.4:80:8080/udp",
        "5.6.7.8:81:8001/tcp",
        "82:8082",
        "9001",
        "9002/udp"
    ]))
    assert ports == {
        "8080/udp": ("1.2.3.4", 80),
        "8001/tcp": ("5.6.7.8", 81),
        "8082/tcp": 82,
        "9001/tcp": 9001,
        "9002/udp": 9002
    }


# noinspection PyShadowingNames
def test_volume_normalization(du):
    assert du.normalize_volume_spec("/path:/my/folder:kjshad:sd:ad:") == [
        "/path", "/my/folder", "kjshad:sd:ad:"
    ]
    assert du.normalize_volume_spec("/1/2") == ["/1/2", "/1/2", "rw"]
    assert du.normalize_volume_spec("/1:/2") == ["/1", "/2", "rw"]
    assert du.normalize_volume_spec("") == ["", "", "rw"]
    with pytest.raises(AttributeError):
        du.normalize_volume_spec(["bla"])


# noinspection PyShadowingNames
def test_basicdockerapp(du):
    cls = du.BasicDockerApp
    assert cls.normalize_image("blabuntu:1.2.3") == ("blabuntu", "1.2.3")
    assert cls.normalize_image("blabuntu:1.2.3:::") == ("blabuntu", "1.2.3:::")
    assert cls.normalize_image("centos") == ("centos", "latest")
    assert cls.normalize_image("") == ("", "latest")
    assert cls.normalize_image_spec(["fedora", "3.2"]) == "fedora:3.2"
    assert cls.volume_args_to_list(["/bla", "/a/b:/c/d", "", "::::::::"]) == [
        "/bla:/bla:rw",
        "/a/b:/c/d:rw",
        "::rw",
        "::::::::"
    ]
