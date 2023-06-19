ARG BUILD_NAME=journey-planner
FROM ${BUILD_NAME}-gtfs-data AS gtfs

FROM python:3-alpine

WORKDIR /data
COPY . .
COPY --from=gtfs /data/gtfs.zip /data/gtfs-raw.zip

ARG GTFS_MODIFICATION_PARAM=''
RUN python ./main.py ${GTFS_MODIFICATION_PARAM} gtfs-raw.zip gtfs.zip \
    && rm gtfs-raw.zip
