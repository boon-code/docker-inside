# Docker Inside

[![Build Status](https://api.travis-ci.com/boon-code/docker-inside.svg)](https://app.travis-ci.com/github/boon-code/docker-inside)
[![PyPI](https://img.shields.io/pypi/v/docker-inside.svg)](https://pypi.python.org/pypi/docker-inside)

`dockerinside` is a Python (Python3 only) package that shall simplify running docker images as the current user
similar to the way *Jenkins* awesome ``docker.inside()`` works.
There are two main use-cases:

- You want to easily share access between a container and your environment without having to
  manually modify the user id and group id of the files created by the running container.
- You want to run *dockerized* GUI applications but share your home environment

You don't have to write a Dockerfile just to adapt to your environment (user id / group id). It is
a much more elegant approach to adapt the environment during startup of the container on the fly as
*Jenkins* does it.


## Installation

Prerequisits:

- Python3 installation (``>= 3.6``)
- `python3-venv` is recommended to create a virtual environment

Install current *stable* version (preferably in a virtual environment):

        pip install git+https://github.com/boon-code/docker-inside.git

For convenience, `dockerinside` uses [su-exec](https://github.com/ncopa/su-exec) which is
statically compiled using `alpine` and `musl-c` library. To build it, you have to run

        # use --auto-pull to download alpine image for compilation if it's not available
        docker-inside-setup --auto-pull

This will create a directory `~/.config/docker_inside/` and put a file named `su-exec` there. You
can also compile `su-exec` and create the file structure yourself or not use it at all. If this
file doesn't exist, `su` is used to switch user id which might cause problems with `tty` handling,
so it's highly recommended to use `su-exec`.


Big thanks to **Natanael Copa** (*ncopa*) for sharing `su-exec`.

### NO\_README

If you experience problems related to packaging the `README.md` or related to
`setuptools` you can disable this behavior using the environment variable
`NO_README` (f.e. `NO_README=1`).

## Usage
### Basic
Running an `ubuntu:16.04` container as current user with the home directory mounted:

        docker-inside -H ubuntu:16.04

which is roughly equivalent to running

        docker run --rm -ti --user "$(id -u)" -v "${HOME}:${HOME}" ubuntu:16.04

but does already add users and groups so you won't see `I have no name!` in your shell prompt.

### Fake Home
You can also use a *fake* home directory

        mkdir -p /tmp/fake-home
        docker-inside --mount-as-home /tmp/fake-home ubuntu:16.04 -- echo "Hello, World" \>~/readme.txt
        #DockerInside : MainThread : INFO : Starting container: 59133ebeb3a3116999f66b4e302ba675a74f02ac83ae526704f2f4cdbd82ed5d
        #DockerInside : MainThread : INFO : Container 59133ebeb3a3116999f66b4e302ba675a74f02ac83ae526704f2f4cdbd82ed5d stopped
        cat /tmp/fake-home/readme.txt
        #Hello, World

### Jenkins Debugging
Sometimes, I just quickly want to debug a problem on a failing *Jenkins* job which uses docker with
lot's of bind mounts which is as simple as this:

        cd <WORKSPACE>
        docker-inside -v <first-mount>:<some-path> \
                      -v <second-mount>:<some-other-path> \
                      -v <WORKSPACE> \
                      -w <WORKSPACE> \
                      <IMAGE_TO_USE> \
                      [optional-command]

### Additional Use-Cases

Please let me know I you need support for more options from original `docker run` command or have
any other suggestions how to improve this package.
Please also let me know if your Docker image is failing using this package and I will see if I can
fix the issue. Adding users and groups is unfortunately quite different among distributions.

## Related

I still use the package myself on a regular basis when using Docker. However, to avoid having to
rely on work-arounds used in this script, `podman` is a simple and powerful replacement for Docker.
`podman` handles user permissions and bind mounts in a sane way per default. Check it out!
