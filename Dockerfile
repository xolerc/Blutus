# ============================================================
# Dockerfile
# ============================================================
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    nmap \
    masscan \
    sqlmap \
    hydra \
    openssh-client \
    netcat \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 5000

CMD ["python", "app.py"]
