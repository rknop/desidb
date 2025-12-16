# docker build -t registry.nersc.gov/desi/rknop/desidb-django:20251212 .

# ======================================================================

FROM debian:bookworm-20251208 AS base
LABEL maintainer="Rob Knop <raknop@lbl.gov>"

ARG UID=95089
ARG GID=45703
# ARG UID=1000
# ARG GID=1000

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ="UTC"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get -y install -y sudo python3 python3-pip python3-venv apache2 libapache2-mod-wsgi-py3 \
                          python3-psycopg2 postgresql-client \
                          libboost-all-dev libcfitsio-dev libblas-dev liblapack-dev libbz2-dev \
                          python3-numpy python3-scipy python3-numba python3-matplotlib \
                          python3-fitsio python3-sqlalchemy python3-yaml python3-pandas \
                          curl git tmux && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /tmp/home
ENV HOME=/tmp/home
WORKDIR /tmp/home

# Note that pyyaml changes how .load works in version 6.0,
#   so desispec breaks with it.
#      pyyaml==5.4.1 \
# Currently using the one from the distro archives (apt-get)

RUN mkdir -p /venv
RUN python3 -mvenv /venv
ENV PATH=/venv/bin:$PATH

RUN source /venv/bin/activate && \
    pip install \
      django==5.2.9 \
      djangorestframework==3.16.1 \
      markdown==3.10 \
      django-filter==25.2 \
      speclite \
      iniparse \
      astropy && \
    rm -rf /tmp/home/.cache/pip


# Install HARP

RUN source /venv/bin/activate && \
    curl -L https://github.com/tskisner/HARP/releases/download/v1.0.5/harp-1.0.5.tar.bz2 -O && \
    tar --no-same-owner -xpf harp-1.0.5.tar.bz2 && \
    cd harp-1.0.5 && \
    ./configure --disable-python --disable-mpi && \
    make -j 8 && \
    make install && \
    cd .. && \
    rm -rf harp-1.0.5 harp-1.0.5.tar.bz2

# Install desi stuff

RUN source /venv/bin/activate && \
    pip install \
       desiutil==3.6.0 \
       desitarget==4.4.0 \
       desispec==0.70.0 \
       desimodel==0.20.0 \
    && rm -rf /tmp/home/.cacahe/pip
       
# I can't figure out the pypi archive for specter.  (I'm not sure I even need this...)

RUN source /venv/bin/activate && \
    git clone https://github.com/desihub/specter && \
    cd specter && \
    git checkout 0.11.0 && \
    python setup.py clean && \
    python setup.py install && \
    cd .. && \
    rm -rf specter

# Set up apache

RUN ln -s ../mods-available/socache_shmcb.load /etc/apache2/mods-enabled/socache_shmcb.load
RUN echo "Listen 8080" > /etc/apache2/ports.conf
COPY 000-default.conf /etc/apache2/sites-available/

# Do scary permissions stuff since we'll have to run
#  as a normal user.  But, given that we're running as
#  a normal user, that makes this less scary.
RUN mkdir -p /var/run/apache2
RUN chmod a+rwx /var/run/apache2
RUN mkdir -p /var/lock/apache2
RUN chmod a+rwx /var/lock/apache2
RUN mkdir -p /var/log/apache2
RUN chmod -R a+rwx /var/log/apache2

RUN mkdir /www
RUN chown $UID:$GID /www
RUN mkdir /www/html
RUN chown $UID:$GID /www/html
RUN mkdir /django
RUN chown $UID:$GID /django

RUN mkdir /home/user
ENV HOME=/home/user
WORKDIR /home/user
RUN chown $UID:$GID /home/user
RUN mkdir /home/user/.astropy
RUN chown $UID:$GID /home/user/.astropy

RUN echo "user:x:$UID:$GID:Django User,,,:/home/user:/bin/bash" >> /etc/passwd
RUN echo "user:*:19034:0:99999:7:::" >> /etc/shadow
RUN echo "user:x:$GID:user" >> /etc/group
RUN echo "user   ALL=(ALL:ALL) ALL" >> /etc/sudoers

# Precompile all python modules; ignore errors
RUN python -m compileall -f "/usr/local/lib/python3.9/dist-packages"; exit 0

USER $UID:$GID

# Make sure astropy has done whatever junk it does upon first import
RUN python -c "import astropy"
RUN python -c "import astropy.io.fits"

# Get the "update" script
COPY update_daily.sh /home/user/update_daily.sh

RUN apachectl start

# Some basic sanity stuff for shell access
ENV LESS=-XLRi

CMD [ "apachectl", "-D", "FOREGROUND", "-D", "APACHE_CONFDIR=/etc/apache2" ]
