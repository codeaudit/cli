#FROM quay.io/pypa/manylinux1_x86_64
#RUN yum -y install rsync git binutils wget && \
#    cp /opt/python/cp27-cp27mu/bin/python /usr/bin/python && \
#    cp /opt/python/cp27-cp27mu/bin/pip /usr/bin/pip

FROM ubuntu:16.04
RUN apt-get -y update && \
    apt-get -y install python-minimal python-dev \
                       wget git rsync binutils upx

RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt pyinstaller

COPY . /src
RUN pyinstaller --clean /src/riseml.spec
RUN mv /dist/riseml /usr/bin/riseml
