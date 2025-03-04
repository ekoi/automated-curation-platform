FROM python:3.12.8-bookworm
LABEL authors="Eko Indarto"


# Combine apt-get commands to reduce layers
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash akmi

ENV PYTHONPATH=/home/akmi/acp/src
ENV BASE_DIR=/home/akmi/acp

WORKDIR ${BASE_DIR}


# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.


# Create and activate virtual environment
RUN python -m venv .venv
ENV APP_NAME="Repository Asistant Service"
ENV PATH="/home/akmi/acp/.venv/bin:$PATH"
# Copy the application into the container.
COPY src ./src
COPY resources ./resources
COPY pyproject.toml .
COPY README.md .
COPY uv.lock .
RUN chmod +x ${BASE_DIR}/resources/utils/ingest.sh

RUN uv venv .venv
# Install dependencies

RUN uv sync --frozen --no-cache

# Run the application.
CMD ["python", "-m", "src.main"]

#CMD ["tail", "-f", "/dev/null"]