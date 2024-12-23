FROM python:3.11.3-slim-bullseye

ARG VERSION=0.5.1

RUN  apt-get update -y && \
     apt-get upgrade -y && \
     apt-get dist-upgrade -y && \
     apt-get install -y git && \
     apt-get install -y curl
#     useradd -ms /bin/bash eee

RUN useradd -ms /bin/bash dans

RUN apt-get update
RUN apt-get install -y git

USER dans
WORKDIR /home/dans
ENV PYTHONPATH=/home/dans/acp/src
ENV BASE_DIR=/home/dans/acp

COPY ./dist/*.* .


RUN mkdir -p ${BASE_DIR} && \
    mkdir -p ${BASE_DIR}/data/db  && \
    mkdir -p ${BASE_DIR}/data/tmp/tus-files  && \
    pip install --no-cache-dir *.whl && rm -rf *.whl && \
    tar xf automated_curation_platform-${VERSION}.tar.gz -C ${BASE_DIR} --strip-components 1 && \
    chmod +x ${BASE_DIR}/resources/utils/ingest.sh

#RUN mkdir -p ${BASE_DIR} && mkdir -p ${BASE_DIR}/data/tmp/bags ${BASE_DIR}/data/tmp/zips  && \
#    pip install --no-cache-dir *.whl && rm -rf *.whl && \
#    tar xf packaging_service-${VERSION}.tar.gz -C ${BASE_DIR} --strip-components 1 && \
#    rm ${BASE_DIR}/conf/*

WORKDIR ${BASE_DIR}

CMD ["python", "src/main.py"]
#CMD ["tail", "-f", "/dev/null"]