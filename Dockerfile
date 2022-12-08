FROM python:3.11.1-alpine AS builder

RUN apk add --update --no-cache gcc musl-dev libffi-dev openssl-dev make cargo
RUN pip install --no-cache-dir build
COPY . /src
RUN python -m build --wheel -o /tmp/dist /src
RUN \
  --mount=type=cache,target=/root/.cache/pip \
    pip wheel /tmp/dist/*.whl --wheel-dir /wheel

FROM python:3.11.1-alpine

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