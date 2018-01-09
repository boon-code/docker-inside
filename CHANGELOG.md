# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2018-01-09
- Add missing information to setup.py

## [0.3.0] - 2018-01-07
### Added
- Update `README.md` how to use the project
- Integrate with *Travis CI* to automate testing and project health

## [0.2.0] - 2018-01-07
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
