FROM python:3.11.9-bullseye

WORKDIR /app

COPY . /app

RUN pip3 install -r requirements.txt