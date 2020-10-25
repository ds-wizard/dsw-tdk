FROM python:3.9-slim

RUN apt-get update && apt-get install -qq -y gcc

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app
RUN pip install .

ENTRYPOINT ["dsw-tdk"]
