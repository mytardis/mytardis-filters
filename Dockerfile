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

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

ADD . /app

CMD ["celery", "worker", "--app=tardis.celery.app", "--queues=filters", "--loglevel=info"]

FROM builder AS test

RUN pip install -r requirements-test.txt

RUN mkdir /var/store

# This will keep container running...
CMD ["tail", "-f", "/dev/null"]
