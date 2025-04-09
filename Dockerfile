FROM python:3.12
ENV PYTHONUNBUFFERED=1

WORKDIR /src

# Systemabhängigkeiten installieren
RUN apt-get update && apt-get install -y libgl1

# CPU-Version von Torch installieren
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Anforderungen installieren
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Projektdateien kopieren
COPY . .

# Start-Skript setzen
ADD /entrypoint.sh /etc/entrypoint.sh
RUN chmod +x /etc/entrypoint.sh
ENTRYPOINT ["/bin/sh", "/etc/entrypoint.sh"]
