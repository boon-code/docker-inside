FROM centos:latest

RUN groupadd -g @@GID@@ @@USER@@
RUN groupadd -g @@EXTGID@@ @@EXTUSER@@
RUN useradd -m -u @@UID@@ -g @@GID@@ @@USER@@
RUN useradd -m -u @@EXTUID@@ -g @@EXTGID@@ @@EXTUSER@@
