# Alternative Dockerfile for running Bitnami variant of ClickHouse on ECS Fargate
ARG BASE_IMAGE=public.ecr.aws/bitnami/clickhouse:latest

FROM ${BASE_IMAGE}

# Bitnami config folder is different from upstream:
COPY ./ecs.config.xml /bitnami/clickhouse/etc/config.d/ecs.config.xml

# Bitnami distro has neither wget nor curl by default - but we need one to run health checks and
# upstream ClickHouse includes wget... So install wget via apt:
# TODO: Resolve whatever GPG signing issue is failing without --allow-insecure-repositories
# (Might not be much we can do about it from our side though?)
USER root
RUN apt-get update --allow-insecure-repositories && \
  apt-get install -y --no-install-recommends wget && \
  rm -rf /var/lib/apt/lists/*
USER 1001
