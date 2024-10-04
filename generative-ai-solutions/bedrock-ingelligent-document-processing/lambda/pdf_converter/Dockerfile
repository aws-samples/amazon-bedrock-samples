
# Define global args
ARG FUNCTION_DIR="/"
ARG RUNTIME_VERSION="3.8"
ARG DISTRO_VERSION="3.12"

# Stage 1 - bundle base image + runtime
# Grab a fresh copy of the image and install GCC
FROM python:${RUNTIME_VERSION}-alpine${DISTRO_VERSION} AS python-alpine

# Install GCC for compiling and linking dependencies
RUN apk add --no-cache \
    libstdc++


# Stage 2 - build function and dependencies
FROM python-alpine AS build-image

# Install Poppler
RUN apk add poppler-utils

# Install Pillow dependencies
RUN apk --no-cache add \
    freetype-dev \
    fribidi-dev \
    harfbuzz-dev \
    jpeg-dev \
    lcms2-dev \
    openjpeg-dev \
    tcl-dev \
    tiff-dev \
    tk-dev \
    zlib-dev

# Install aws-lambda-cpp build dependencies
RUN apk add --no-cache \
    build-base \
    libtool \
    autoconf \
    automake \
    libexecinfo-dev \
    make \
    cmake \
    libcurl

# Include global args in this stage of the build
ARG FUNCTION_DIR
ARG RUNTIME_VERSION

# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy requirements function
COPY app/requirements.txt ${FUNCTION_DIR}

# Install the function's dependencies
RUN python${RUNTIME_VERSION} -m pip install -r ${FUNCTION_DIR}requirements.txt --target ${FUNCTION_DIR}

# Copy handler function
COPY app/main.py ${FUNCTION_DIR}

# Stage 3 - final runtime image

# Grab a fresh copy of the Python image
FROM python-alpine

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "main.lambda_handler" ]