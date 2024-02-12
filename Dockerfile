# syntax=docker/dockerfile:1.4

FROM python:3.12.2-alpine AS builder
SHELL ["/bin/ash", "-o", "pipefail", "-c"]
ENV CC='ccache gcc'

RUN \
    apk add --update --no-cache gcc ccache musl-dev libffi-dev \
    && pip install --no-cache-dir build
COPY poetry.lock pyproject.toml /src/
COPY get_oracle_a1 /src/get_oracle_a1
RUN python -m build --wheel -o /tmp/dist /src
RUN \
  --mount=type=cache,target=/root/.cache/pip \
  --mount=type=cache,target=/root/.cache/ccache \
    pip wheel /tmp/dist/*.whl --wheel-dir /wheel

FROM python:3.12.2-alpine

MAINTAINER 'Byeonghoon Isac Yoo <bh322yoo@gmail.com>'

RUN \
  --mount=type=bind,target=/wheel,from=builder,source=/wheel \
  --mount=type=bind,target=/tmp/wheel,from=builder,source=/tmp/dist \
    pip install \
      --no-cache-dir \
      --no-index \
      --find-links=/wheel \
      /tmp/wheel/*.whl

ENTRYPOINT ["/usr/local/bin/get_oracle_a1"]