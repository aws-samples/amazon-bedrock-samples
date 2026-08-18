# FROM public.ecr.aws/docker/library/python:3.10-slim
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN  pip3 install --upgrade pip && pip3 install -r requirements.txt

WORKDIR /app

COPY /app .

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0" ]