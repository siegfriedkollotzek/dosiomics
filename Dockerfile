FROM python:3.12
ENV PYTHONUNBUFFERED=1

WORKDIR /src

RUN apt-get update && apt-get install libgl1 -y
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ADD /entrypoint.sh /etc/entrypoint.sh
ENTRYPOINT ["/bin/sh", "/etc/entrypoint.sh"]
