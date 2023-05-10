FROM python:3.10-slim

WORKDIR /src

COPY ./requirements.txt ./requirements.txt

RUN python -m pip install -r requirements.txt

USER 1000

COPY simulator/ ./simulator

CMD ["python", "simulator"]