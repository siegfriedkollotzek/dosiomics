FROM python:3.12
ENV PYTHONUNBUFFERED=1

WORKDIR /src
COPY ./requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install libgl1 -y

COPY . .

ADD /entrypoint.sh /etc/entrypoint.sh
ENTRYPOINT ["/bin/sh", "/etc/entrypoint.sh"]
