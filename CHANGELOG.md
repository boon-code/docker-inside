# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.14] - 2018-07-07
### Added
- Show return code of the running containers with log level info (default) for `docker-inside` and
  `docker-inside-setup`. This also ensures that `docker-inside-setup` at least outputs a line
  about whether it succeeded or failed.
### Changed
- Update local development environment (`requirements.txt`) as there were some false negatives with
  my current setup (due to `pytest` version?).
### Fixed
- Avoid parameter `exist_ok` of `os.makedirs` as some versions of Python have a broken
  implementation it seems.
- Read output from `docker-inside-setup` command and show it if `--verbose` flag is used.

## [0.3.13] - 2018-06-14
### Added
- Added integration test case for `docker-inside-setup` package verifying basic function.
### Fixed
- Fix broken `docker-inside-setup` command (regression from `0.3.11`). Extend test cases to prevent
  further regressions.

## [0.3.12] - 2018-05-27
### Fixed
- Fix broken arguments related to bind mounts (introduced in `0.3.11`)

## [0.3.11] - 2018-05-27
### Fixed
- Fix volumes specification handling. It's now possible to mount one host path multiple times
  to different locations in the container image (f.e. with different access modes) as this is
  possible with `docker run`.
- Fix precedence of environment variables: First lookup the image, then use environment variables
  from command line.

## [0.3.10] - 2018-05-26
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

[Unreleased]: https://github.com/boon-code/docker-inside/compare/0.3.14...HEAD
[0.3.14]: https://github.com/boon-code/docker-inside/compare/0.3.13...0.3.14
[0.3.13]: https://github.com/boon-code/docker-inside/compare/0.3.12...0.3.13
[0.3.12]: https://github.com/boon-code/docker-inside/compare/0.3.11...0.3.12
[0.3.11]: https://github.com/boon-code/docker-inside/compare/0.3.10...0.3.11
[0.3.10]: https://github.com/boon-code/docker-inside/compare/0.3.9...0.3.10
[0.3.9]: https://github.com/boon-code/docker-inside/compare/0.3.8...0.3.9
[0.3.8]: https://github.com/boon-code/docker-inside/compare/0.3.7...0.3.8
[0.3.7]: https://github.com/boon-code/docker-inside/compare/0.3.6a1...0.3.7
[0.3.6]: https://github.com/boon-code/docker-inside/compare/0.3.5...0.3.6a1
[0.3.5]: https://github.com/boon-code/docker-inside/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/boon-code/docker-inside/compare/0.3.1...0.3.4
[0.3.1]: https://github.com/boon-code/docker-inside/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/boon-code/docker-inside/compare/0.2.0...0.3.0
