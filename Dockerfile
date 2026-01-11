ARG PYTHON_VERSION=3.13
ARG DEBIAN_VERSION=trixie
ARG BASE_IMG=python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
ARG PYTHON_SITE_PKGS=/usr/local/lib/python${PYTHON_VERSION}/site-packages

FROM $BASE_IMG AS builder
ARG PYTHON_SITE_PKGS
WORKDIR /app

COPY pyproject.toml .
RUN pip install --prefer-binary --compile --no-cache-dir --group all
COPY src ./src
RUN pip install --prefer-binary --compile --no-cache-dir .
RUN cd $PYTHON_SITE_PKGS && rm -rf pip* setuptools* wheel*

FROM $BASE_IMG
ARG PYTHON_SITE_PKGS

COPY --from=builder $PYTHON_SITE_PKGS $PYTHON_SITE_PKGS
COPY --from=builder /usr/local/bin /usr/local/bin

ENV PYTHONUNBUFFERED=1
EXPOSE 9001
WORKDIR /app
CMD ["hypercorn", "-w", "4", "-b", "0.0.0.0:9001", "ayase_quart.main:app"]
