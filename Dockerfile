FROM python:3.9.6-alpine AS builder
RUN wget -O - https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
COPY . .
RUN source $HOME/.poetry/env && poetry build -f wheel

FROM python:3.9.6-alpine
COPY --from=builder dist/*.whl ./
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    libffi-dev \
    musl-dev \
    openssl-dev \
    && apk add openssl \
    && pip install --no-cache-dir *.whl \
    && apk del .build-deps \
    && rm -rf *.whl
ENTRYPOINT ["python", "-m", "get_oracle_a1"]
