from setuptools import setup, find_packages
import datetime
import os

YEAR = datetime.date.today().year

__author__ = "Manuel Huber"
__version__ = "0.3.17"
__license__ = "MIT"
__copyright__ = u'%s, Manuel Huber' % YEAR


# Add Travis build id if not deploying a release (tag)
if os.environ.get("TRAVIS", "") == "true":
    build_id = os.environ["TRAVIS_BUILD_NUMBER"]
    tag = os.environ.get("TRAVIS_TAG", "")
    if tag:
        if __version__ != tag:
            raise RuntimeError(
                    "tag != version: {0}, {1}".format(tag, __version__))
    else:
        __version__ = "{0}.{1}".format(__version__, build_id)

setup_extra = dict()
if os.environ.get("NO_README", "") == "":
    with open('README.md') as f:
        setup_extra['long_description'] = f.read()
    setup_extra['long_description_content_type'] = 'text/markdown'
    setup_extra['setup_requires'] = [
        'setuptools>=38.6.0'
    ]


setup(
    name='docker-inside',
    version=__version__,
    description='Run a docker container with you workspace and user',
    url="https://github.com/boon-code/docker-inside",
    license=__license__,
    author=__author__,
    author_email='Manuel.h87@gmail.com',
    classifiers=["Development Status :: 3 - Alpha",
                 "License :: OSI Approved :: MIT License",
                 "Programming Language :: Python :: 3 :: Only",
                 "Topic :: System :: Systems Administration"],
    package_dir={
        '': 'src'
    },
    packages=find_packages(where='./src'),
    entry_points={
        'console_scripts': [
            'din = dockerinside.__init__:main',
            'docker-inside = dockerinside.__init__:main',
            'docker_inside = dockerinside.__init__:main',
            'dockerinside = dockerinside.__init__:main',
            'din-setup = dockerinside.setup.__init__:setup_main',
            'docker-inside-setup = dockerinside.setup.__init__:setup_main',
            'docker_inside_setup = dockerinside.setup.__init__:setup_main',
        ]
    },
    install_requires=[
        "argparse>=1.4.0",
        "argcomplete>=1.4.1",
        "docker>=2.7.0",
        "dockerpty>=0.4.1"
    ],
    **setup_extra
)
