# docker build -t registry.nersc.gov/desi/rknop/desidb-django:20251216 .

# ======================================================================

FROM debian:bookworm-20251208 AS base
LABEL maintainer="Rob Knop <raknop@lbl.gov>"

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ="UTC"

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y install -y \
        sudo \
        python3 \
        postgresql-client \
        libcfitsio-bin \
        libbz2-1.0 \
        curl \
        git \
        tmux \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
        

RUN mkdir /tmp/home
ENV HOME=/tmp/home
WORKDIR /tmp/home

# ======================================================================

FROM base AS build

RUN apt-get update \
    && apt-get -y install -y \
         autoconf \
         autotools-dev \
         cmake \
         cython3 \
         g++ \
         gdb \
         gfortran \
         libbz2-dev \
         libcfitsio-dev \
         pkg-config \
         libtool \
         python3-pip \
         python3-venv \
   && apt-get -y autoremove \
   && apt-get clean

RUN mkdir -p /venv
RUN python3 -mvenv /venv

RUN source /venv/bin/activate && \
    pip install \
      astropy==7.2.0 \
      psycopg==3.3.2 \
      numpy==2.3.5 \
    && rm -rf /tmp/home/.cache/pip

# ======================================================================

FROM base AS shell

COPY --from=build /venv /venv
ENV PATH="/venv/bin:$PATH"
CMD [ "tail", "-f", "/etc/issue" ]
