FROM python:3.11.4-bullseye

WORKDIR /ayase_quart/src

COPY . .

VOLUME /ayase_quart/src/logs

RUN pip install -r requirements.txt

# assumes you have SSL certs set up
CMD ["hypercorn", "--workers=2", "--bind=0.0.0.0:8080", "--certfile=cert.pem", "--keyfile=key.pem", "main:app"]
