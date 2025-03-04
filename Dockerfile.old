FROM python:3.12.8-bookworm
LABEL authors="Eko Indarto"

# Combine apt-get commands to reduce layers
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Install Poetry using the official installation script
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to the PATH
ENV PATH="/root/.local/bin:$PATH"

RUN useradd -ms /bin/bash akmi

ENV PYTHONPATH=/home/akmi/acp/src
ENV BASE_DIR=/home/akmi/acp

WORKDIR ${BASE_DIR}

COPY pyproject.toml .
COPY README.md .
COPY src ./src
COPY resources ./resources


RUN  poetry install
RUN  poetry build
RUN  pip install --no-cache-dir dist/*.whl && rm -rf dist/*.whl && chmod +x ${BASE_DIR}/resources/utils/ingest.sh

RUN chown -R akmi:akmi ${BASE_DIR}


USER akmi
CMD ["python", "src/main.py"]
#CMD ["tail", "-f", "/dev/null"]