FROM rknop/devuan-chimaera-rknop
MAINTAINER Rob Knop <raknop@lbl.gov>

# ARG UID=95089
# ARG GID=45703
ARG UID=1000
ARG GID=1000

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y sudo python3 python3-pip apache2 libapache2-mod-wsgi-py3 \
                       python3-psycopg2 postgresql-client \
                       libboost-all-dev libcfitsio-dev libblas-dev liblapack-dev libbz2-dev \
                       python3-numpy python3-scipy python3-numba python3-matplotlib \
                       python3-fitsio python3-sqlalchemy python3-yaml python3-pandas \
                       curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN mkdir /tmp/home
ENV HOME /tmp/home
WORKDIR /tmp/home

# Note that pyyaml changes how .load works in version 6.0,
#   so desispec breaks with it.
#      pyyaml==5.4.1 \
# Currently using the one from the distro archives (apt-get)

RUN pip3 install \
      django==4.0.2 \
      djangorestframework==3.13.1 \
      markdown==3.3.6 \
      django-filter==21.1 \
      speclite \
      iniparser \
      astropy && \
    rm -rf /tmp/home/.cache/pip


# Install HARP

RUN curl -L https://github.com/tskisner/HARP/releases/download/v1.0.5/harp-1.0.5.tar.bz2 -O && \
    tar --no-same-owner -xpf harp-1.0.5.tar.bz2 && \
    cd harp-1.0.5 && \
    ./configure --disable-python --disable-mpi && \
    make -j 8 && \
    make install && \
    cd .. && \
    rm -rf harp-1.0.5 harp-1.0.5.tar.bz2

# Install desispec

RUN git clone https://github.com/desihub/desiutil && \
    cd desiutil && \
    git checkout 3.2.5 && \
    python setup.py clean && \
    python setup.py install && \
    cd .. && \
    rm -rf desiutil

RUN git clone https://github.com/desihub/desitarget && \
    cd desitarget && \
    git checkout 2.4.0 && \
    python setup.py clean && \
    python setup.py install && \
    cd .. && \
    rm -rf desitarget

RUN git clone https://github.com/desihub/desispec && \
    cd desispec && \
    git checkout 0.51.11 && \
    python setup.py clean && \
    python setup.py install && \
    cd .. && \
    rm -rf desispec

RUN git clone https://github.com/desihub/desimodel && \
    cd desimodel && \
    git checkout 0.17.0 && \
    python setup.py clean && \
    python setup.py install && \
    cd .. && \
    rm -rf desimodel

RUN git clone https://github.com/desihub/specter && \
    cd specter && \
    git checkout 0.10.0 && \
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
ENV HOME /home/user
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

RUN apachectl start

CMD [ "apachectl", "-D", "FOREGROUND", "-D", "APACHE_CONFDIR=/etc/apache2" ]
