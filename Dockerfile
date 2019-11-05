FROM mytardis/filters-essentials AS base

ENV C_FORCE_ROOT 1
ENV LOG_LEVEL info
ENV CONCURRENCY 1

ENV FILTERS_Q filters

ENV RMQ_HOST rabbitmq
ENV RMQ_PORT 5672

RUN apt-get update && apt-get -y install netcat && apt-get clean
RUN pip3 install -U pip

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

ADD . /app

COPY docker-entrypoint.sh /
RUN ["chmod", "+x", "/docker-entrypoint.sh"]
ENTRYPOINT ["/docker-entrypoint.sh"]

FROM base AS test

RUN pip3 install -r requirements-test.txt

RUN mkdir /var/store
COPY filters/tests/assets /var/store
