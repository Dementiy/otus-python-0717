#!/bin/sh
set -xe

yum install -y  gcc \
				make \
				protobuf \
				protobuf-c \
				protobuf-c-compiler \
				protobuf-c-devel \
				python-devel \
				python-setuptools \
				gdb 

ulimit -c unlimited
cd /tmp/otus/
protoc-c --c_out=. deviceapps.proto
python setup.py test
