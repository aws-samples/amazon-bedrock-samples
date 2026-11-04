FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Install build dependencies for numpy and other packages that need compilation
RUN yum install -y gcc gcc-c++ make python3-devel && yum clean all

COPY requirements.txt .
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY . ${LAMBDA_TASK_ROOT}

WORKDIR ${LAMBDA_TASK_ROOT}

CMD [ "preprocess.lambda_handler" ]