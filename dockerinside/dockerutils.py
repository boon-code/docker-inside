import os
import abc

import docker
import docker.tls


class ContainerError(RuntimeError):
    def __init__(self, cname, *args):
        RuntimeError.__init__(self, *args)
        self.container = cname


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
        if isinstance(image_spec, abc.Sequence):
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

    def __init__(self, log, env=None):
        self._log = log
        _, params = self._get_client_config(env)
        self._dc = self._create_docker_client(params)

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
