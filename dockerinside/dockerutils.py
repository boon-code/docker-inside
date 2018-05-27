import os
import grp
import tarfile
import tempfile
import collections.abc

import docker
import docker.errors


class ContainerError(RuntimeError):
    def __init__(self, cname, *args):
        RuntimeError.__init__(self, *args)
        self.container = cname


class InvalidContainerState(ContainerError):
    def __init__(self, cname, state):
        text = "Container '{0}' in invalid state '{1}'".format(cname, state)
        ContainerError.__init__(self, cname, text)
        self.state = state


class InvalidPath(RuntimeError):
    def __init__(self, path, type_):
        text = "Invalid path '{0}': Required type {1}".format(path, type_)
        RuntimeError.__init__(self, text)
        self.path = path
        self.type_ = type_


class MissingImageError(RuntimeError):
    def __init__(self, image, tag='latest', pull=False):
        if pull:
            text = "Couldn't pull image '{0}:{1}'".format(image, tag)
        else:
            text = "Missing image '{0}:{1}'".format(image, tag)
        RuntimeError.__init__(self, text)
        self.image = image
        self.tag = tag
        self.pull = pull

    @property
    def fullname(self):
        return "{0}:{1}".format(self.image, self.tag)


def _assert_path_exists(path, type_=None):
    abs_path = os.path.abspath(path)
    if type_ == 'directory':
        if not os.path.isdir(abs_path):
            raise InvalidPath(abs_path, type_)
    elif type_ == 'file':
        if not os.path.isfile(abs_path):
            raise InvalidPath(abs_path, type_)
    else:
        if not os.path.exists(abs_path):
            raise InvalidPath(abs_path, '')


def env_list_to_dict(env_list, host_env=None):
    """Generator to convert environemnt list to dictionary

    :param env_list: List of environment variables in format 'VARIABLE=VALUE'
    :param host_env: Optional host environment will be looked up, if '=VALUE'
                     part is missing.
    """
    if host_env is None:
        host_env = os.environ
    if env_list is None:
        env_list = []
    for i in env_list:
        tmp = i.split("=", 1)
        if len(tmp) == 2:
            yield tmp[0], tmp[1]
        else:
            if tmp[0] in host_env.keys():
                yield tmp[0], host_env[tmp[0]]


def split_port_normalized(port_spec, default_protocol='tcp'):
    v = port_spec.split('/', 1)
    if len(v) == 2:
        return int(v[0]), v[1]
    else:
        return int(v[0]), default_protocol


def normalize_port(port_spec, **kwargs):
    return "{0}/{1}".format(*split_port_normalized(port_spec, **kwargs))


def normalize_volume_spec(spec):
    mode = 'rw'
    tmp = spec.split(":", 2)
    if len(tmp) == 3:
        pass
    elif len(tmp) == 2:
        tmp.append(mode)
    elif len(tmp) == 1:
        tmp.append(tmp[0])
        tmp.append(mode)
    else:
        raise ValueError("Wrong volume spec: '{0}".format(i))
    return tmp


def volume_spec_to_string(spec):
    return "{0}:{1}:{2}".format(*spec)


def port_list_to_dict(port_list):
    if port_list is None:
        port_list = []
    for i in port_list:
        tmp = i.split(":", 2)
        if len(tmp) == 3:
            host_map = (tmp[0], split_port_normalized(tmp[1])[0])
            yield normalize_port(tmp[2]), host_map
        elif len(tmp) == 2:
            yield normalize_port(tmp[1]), split_port_normalized(tmp[0])[0]
        else:
            yield normalize_port(tmp[0]), split_port_normalized(tmp[0])[0]


def tmpfs_list_to_dict(tmpfs_list):
    """Transform list of tmpfs parameters to dictionary

    :param tmpfs_list: List of tmpfs entry (of form 'directory:options')
    :returns: Dictionary as needed by Docker API
    """
    d = dict()
    for i in tmpfs_list:
        tmpfs_spec = i.split(':', 1)
        if len(tmpfs_spec) == 1:
            d[tmpfs_spec[0]] = ""
        else:
            d[tmpfs_spec[0]] = tmpfs_spec[1]
    return d


def tar_pack(data, write_mode='w', default_mode=0o640):
    def _add_file(archive, name, payload, mode):
        ti = tarfile.TarInfo(name)
        ti.uid = 0
        ti.gid = 0
        ti.mode = mode
        ti.uname = "root"
        ti.gname = "root"
        with tempfile.TemporaryFile(prefix='docker-file') as f:
            f.write(payload)
            f.flush()
            ti.size = f.tell()
            f.seek(0)
            archive.addfile(ti, f)

    with tempfile.TemporaryFile(prefix='docker-archive') as archf:
        arch = tarfile.open(fileobj=archf, mode=write_mode)
        for k, v in data.items():
            if 'mode' not in v:
                v['mode'] = default_mode
            if 'file' in v:
                arch.add(v['file'], arcname=k)
            else:
                _add_file(arch, k, v.get('payload', b''), v['mode'])
        arch.close()
        archf.flush()
        archf.seek(0)
        data = archf.read()
        return data


def get_user_groups(username):
    return list([g for g in grp.getgrall() if username in g.gr_mem])


def _split_and_filter(args):
    for i in args:
        parts = i.split('/')
        for j in parts:
            if j != '':
                yield j


def linux_pjoin(*args):
    """ Joins arguments as if they were linux paths, directories, files

    :param args: Parts of a path to join
    """
    root = ''
    if args[0].startswith('/'):
        root = '/'
    parts = _split_and_filter(args)
    rpath = "/".join(parts)
    return root + rpath


class BasicDockerApp(object):

    @classmethod
    def normalize_image(cls, image_spec):
        tmp = image_spec.split(":", 1)
        if len(tmp) == 1:
            return tmp[0], 'latest'
        elif len(tmp) == 2:
            return tmp
        else:
            raise ValueError("Invalid image specification: '{0}'".format(image_spec))

    @classmethod
    def normalize_image_spec(cls, image_spec):
        if isinstance(image_spec, collections.abc.Sequence):
            seq = image_spec
        else:
            seq = cls.normalize_image(image_spec)
        return ":".join(seq)

    @staticmethod
    def combine_image_spec(image, tag):
        return ":".join((image, tag))

    @staticmethod
    def _assert_state(cname, cfg, *allowed_states):
        status = cfg['State']['Status']
        if status not in allowed_states:
            raise InvalidContainerState(cname, status)

    @staticmethod
    def volume_args_to_list(args):
        l = list()
        for i in args:
            l.append(volume_spec_to_string(normalize_volume_spec(i)))
        return l

    def __init__(self, log, env=None):
        self._log = log
        self._env = env
        self._dc = docker.from_env(environment=env)

    def _assert_image_available(self, image_spec, auto_pull=False):
        img, tag = self.normalize_image(image_spec)
        image_spec = self.combine_image_spec(img, tag)  # ensure full image spec
        try:
            self._dc.images.get(image_spec)
            self._log.debug("Found image '{0}' locally".format(image_spec))
        except docker.errors.ImageNotFound:
            if auto_pull:
                self._log.warning("Image '{0}' not found locally -> pull it".format(image_spec))
                self._dc.images.pull(img, tag)
            else:
                raise
