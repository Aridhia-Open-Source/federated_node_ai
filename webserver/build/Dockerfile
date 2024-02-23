FROM python:3.12

COPY app /app
COPY migrations /migrations
COPY alembic.ini /

WORKDIR /app

# hadolint detects pipenv as another invocation of pip
# hadolint ignore=DL3013
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
        libpq-dev \
        python3-dev \
        gcc \
    && pip install --upgrade pip \
    && PATH=$(which pg_config):$PATH \
    && python3 -m pip install --no-cache-dir pipenv \
    && pipenv lock \
    && pipenv install --system --deploy --categories packages \
    && pip uninstall -y pipenv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5000
WORKDIR /
ENTRYPOINT [ "waitress-serve", "--host=0.0.0.0", "--port=5000", "--call", "app:create_app"]
