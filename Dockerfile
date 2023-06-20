ARG BUILD_NAME=journey-planner
FROM ${BUILD_NAME}-gtfs-data AS gtfs

FROM python:3-alpine AS modify

# Unbuffered output, otherwise output appears with great delay
ENV PYTHONUNBUFFERED=1

WORKDIR /data
COPY . .
COPY --from=gtfs /data/gtfs.zip /data/input.zip

ARG GTFS_MODIFICATION_PARAM=''
RUN python ./main.py ${GTFS_MODIFICATION_PARAM} input.zip gtfs.zip \
    && rm input.zip

FROM scratch
COPY --from=modify /data/gtfs.zip /data/gtfs.zip
