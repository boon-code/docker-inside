# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [0.3.10] - 2018-05-23
### Added
- Added support for `--tmpfs` (as in `docker run`) which allows to mount temporary directories
  inside of docker containers

## [0.3.9] - 2018-05-13
### Added
- Added `--mount-workdir` option which simplifies to mount a work space and set it as working
  directory (`-v /host/path:/container/path` and `-w /container/path`)

## [0.3.8] - 2018-02-18
### Added
- Added simple `--gui` option to mount X11 socket and set `DISPLAY` environment variable.
- Added `--init` option to use init (`tini`) service in container.
### Fixed
- Fixed environment option to use host environment if `=`-part is missing in environment
  specification

## [0.3.7] - 2018-01-20
### Added
- Add automatic deployment to PyPI
### Changed
- Deploy all commits on master to test.pypi.org

## [0.3.6] - 2018-01-20
### Fixed
- Install `pandoc` for travis CI deployment

## [0.3.5] - 2018-01-20
### Added
- Add `--switch-root` flag to enforce starting the container as root (`docker-inside` will still
  switch to your user afterwards). Might become default behavior.

## [0.3.4] - 2018-01-09
### Fixed
- Fix documentation for pypi

## [0.3.1] - 2018-01-09
### Added
- Add missing information to setup.py

## [0.3.0] - 2018-01-07
### Added
- Update `README.md` how to use the project
- Integrate with *Travis CI* to automate testing and project health

## 0.2.0 - 2018-01-07
### Added
- Run a basic test for `ubuntu`, `busybox`, `alpine`, `centos` and `fedora`
- Add support for `centos` and `fedora` images by checking commands to add users/groups and
  work around platform specific differences (as `centos` symlinking `adduser` to `useradd`).
- Allow to mount the current home directory (`--mount-home`), some local directory as home
  directory (`--mount-as-home`) or create a temporary home directory in the container (`--tmp-home`).
- Allow to compile `su-exec` a using `alpine:3.6` using `docker-inside-setup` command and use this
  binary to change user (which is better than `su -l` regarding `tty` handling).
- Use `busybox` for user/group creation if both applets are available.
- Skip already existing group id's.
- Create unit tests using `pytest`.
- Generate `.gitignore` using http://gitignore.io website.
- Publish the project under MIT license.

[Unreleased]: https://github.com/boon-code/docker-inside/compare/0.3.10...HEAD
[0.3.10]: https://github.com/boon-code/docker-inside/compare/0.3.9...0.3.10
[0.3.9]: https://github.com/boon-code/docker-inside/compare/0.3.8...0.3.9
[0.3.8]: https://github.com/boon-code/docker-inside/compare/0.3.7...0.3.8
[0.3.7]: https://github.com/boon-code/docker-inside/compare/0.3.6a1...0.3.7
[0.3.6]: https://github.com/boon-code/docker-inside/compare/0.3.5...0.3.6a1
[0.3.5]: https://github.com/boon-code/docker-inside/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/boon-code/docker-inside/compare/0.3.1...0.3.4
[0.3.1]: https://github.com/boon-code/docker-inside/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/boon-code/docker-inside/compare/0.2.0...0.3.0
