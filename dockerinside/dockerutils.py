import os
import grp
import tarfile
import tempfile
import collections.abc

import docker
import docker.tls


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


def env_list_to_dict(env_list):
    for i in env_list:
        key, value = env_list.split("=", 1)
        yield key, value


def tar_pack(data, write_mode='w', default_mode=0o640):
    def _add_file(arch, name, payload, mode):
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
            arch.addfile(ti, f)

    with tempfile.TemporaryFile(prefix='docker-archive') as archf:
        arch = tarfile.open(fileobj=archf, mode=write_mode)
        for k, v in data.items():
            if 'mode' not in v: v['mode'] = default_mode
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
    def _create_tls_config(cls, cert_path):
        client_cert = (os.path.join(cert_path, 'cert.pem'),
                       os.path.join(cert_path, 'key.pem'))
        cfg = docker.tls.TLSConfig(
            client_cert=client_cert,
            ca_cert=os.path.join(cert_path, 'ca.pem'),
            verify=True
        )
        return cfg

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

    @classmethod
    def _create_docker_client(cls, params):
        return docker.Client(**params)

    @staticmethod
    def _assert_state(cname, cfg, *allowed_states):
        status = cfg['State']['Status']
        if status not in allowed_states:
            raise InvalidContainerState(cname, status)

    @staticmethod
    def volume_args_to_dict(args):
        d = dict()
        for i in args:
            mode = 'rw'
            tmp = i.split(":", 2)
            if len(tmp) == 3:
                mode = tmp[2]
            elif len(tmp) == 2:
                pass
            elif len(tmp) == 1:
                tmp.append(tmp[0])
            else:
                raise ValueError("Wrong volume spec: '{0}".format(i))
            d[tmp[0]] = dict(bind=tmp[1], mode=mode)

    def __init__(self, log, env=None):
        self._log = log
        _, params = self._get_client_config(env)
        self._dc = self._create_docker_client(params)

    def _assert_image_available(self, image_spec, auto_pull=False):
        img, tag = self.normalize_image(image_spec)
        image_spec = self.combine_image_spec(img, tag)
        r = self._dc.images(image_spec)
        if not r:
            if auto_pull:
                self._dc.pull(img, tag)
                r = self._dc.images(image_spec)
                if not r:
                    raise MissingImageError(img, tag, True)
            else:
                raise MissingImageError(img, tag, False)

    def _get_client_config(self, env=None):
        if env is None:
            env = os.environ
        kw = dict()
        try:
            tls_verify = env['DOCKER_TLS_VERIFY']
            self._log.debug("Found env. variable DOCKER_TLS_VERIFY: {0}".format(tls_verify))
            kw['base_url'] = env['DOCKER_HOST']
            self._log.debug("Found env. variable DOCKER_HOST: {0}".format(kw['base_url']))
            cert_p = env['DOCKER_CERT_PATH']
            self._log.debug("Found env. variable DOCKER_CERT_PATH: {0}".format(cert_p))
            kw['tls'] = self._create_tls_config(cert_p)
            return True, kw
        except KeyError:
            self._log.debug("Use local docker installation")
            return False, dict()
