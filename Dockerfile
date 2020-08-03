FROM python:slim

MAINTAINER LightQuantum

WORKDIR /app

RUN pip install --upgrade --no-cache-dir pip

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY crazy_dave ./crazy_dave

CMD ["python", "-m", "crazy_dave.__main__"]