FROM python:3.9-slim

RUN apt-get update && apt-get install -qq -y gcc=4:10.2.1-1 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app
RUN pip install .

ENTRYPOINT ["dsw-tdk"]
