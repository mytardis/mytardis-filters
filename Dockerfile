FROM ubuntu:18.10 AS base

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -yqq && \
	apt-get install -yqq --no-install-recommends \
		mc \
		htop \
		# Generic
		curl \
		git \
		apt-transport-https \
		build-essential \
		# SSL
		libsasl2-dev \
		libssl-dev \
		# Python
		python-dev \
		python-pip \
		python-setuptools \
		python-magic \
		# C
		gcc \
		# Java
		openjdk-8-jdk \
		# R
		r-base \
		r-base-dev \
		# ImageMagick
		ghostscript \
		libx11-dev \
		libxext-dev \
		zlib1g-dev \
		libpng-dev \
		libjpeg-dev \
		libfreetype6-dev \
		libxml2-dev \
		libmagic-dev \
		libmagickwand-dev \
		# Filters
		gnumeric \
		imagemagick && \
	apt-get clean

RUN pip install wheel

RUN echo "r <- getOption('repos'); r['CRAN'] <- 'https://cran.csiro.au/'; options(repos = r);" > ~/.Rprofile
RUN Rscript -e "install.packages('BiocManager')"
RUN Rscript -e "BiocManager::install('flowCore', version='3.8')"
RUN Rscript -e "BiocManager::install('flowViz', version='3.8')"

COPY policy.xml /etc/ImageMagick-6/policy.xml

FROM base AS builder

ADD . /app

WORKDIR /app

RUN pip install -r requirements.txt

FROM builder AS run

# RUN mkdir -p tardis/tardis_portal/filters

# RUN pip install git+https://github.com/mytardis/mytardisbf.git@0.1.1#egg=mytardisbf

# RUN git clone https://github.com/mytardis/mytardisbf.git tardis/tardis_portal/filters/mytardisbf
RUN pip install -r tardis/tardis_portal/filters/mytardisbf/requirements.txt

# RUN git clone https://github.com/mytardis/fcs-mytardis-filter.git tardis/tardis_portal/filters/fcs
RUN pip install -r tardis/tardis_portal/filters/fcs/requirements.txt

# RUN git clone https://github.com/mytardis/pdf-mytardis-filter.git tardis/tardis_portal/filters/pdf

# RUN git clone https://github.com/mytardis/xlsx-mytardis-filter.git tardis/tardis_portal/filters/xlsx

# RUN git clone https://github.com/mytardis/csv-mytardis-filter tardis/tardis_portal/filters/csv

CMD ["celery", "worker", "--app=tardis.celery.tardis_app", "--queues=filters", "--loglevel=info"]
