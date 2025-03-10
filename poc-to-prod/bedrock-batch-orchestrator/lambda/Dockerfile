FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY . ${LAMBDA_TASK_ROOT}

WORKDIR ${LAMBDA_TASK_ROOT}

CMD [ "preprocess.lambda_handler" ]