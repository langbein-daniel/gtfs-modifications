ARG BUILD_NAME=journey-planner
FROM ${BUILD_NAME}-gtfs-data-raw AS gtfs

FROM python:3

WORKDIR /data
COPY . .
COPY --from=gtfs /data/gtfs.zip /data/gtfs-raw.zip

RUN python ./main.py gtfs-raw.zip gtfs.zip \
    && rm gtfs-raw.zip
