from setuptools import setup
import datetime

YEAR = datetime.date.today().year

__author__ = "Manuel Huber"
__version__ = "0.1.2"
__license__ = "MIT"
__copyright__ = u'%s, Manuel Huber' % YEAR

setup(
    name='docker-inside',
    version=__version__,
    description='Run a docker container with you workspace and user',
    license=__license__,
    author=__author__,
    author_email='Manuel.h87@gmail.com',
    classifiers=["Development Status :: 3 - Alpha",
                 "License :: OSI Approved :: MIT License",
                 "Programming Language :: Python :: 3 :: Only",
                 "Topic :: System :: Systems Administration"],
    packages=['dockerinside'],
    entry_points={
        'console_scripts':
            ['din = dockerinside.__init__:main']},
    install_requires=["argparse>=1.4.0",
                      "argcomplete>=1.4.1",
                      "blessings>=1.6",
                      "docker-py>=1.5.0",
                      "dockerpty>=0.4.1"],
)