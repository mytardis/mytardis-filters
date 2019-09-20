FROM mytardis/filters-essentials AS base

ENV LOG_LEVEL info

FROM base AS builder

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

ADD . /app

CMD ["celery", "worker", "--app=tardis.celery.app", "--queues=filters", "--loglevel=${LOG_LEVEL}"]

FROM builder AS test

RUN pip3 install -r requirements-test.txt

RUN mkdir /var/store

# This will keep container running...
CMD ["tail", "-f", "/dev/null"]
