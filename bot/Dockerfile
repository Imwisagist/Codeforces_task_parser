FROM python:3.7-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get upgrade -y && \
    pip install --upgrade pip && pip install -r requirements.txt

COPY . .

CMD ["python3", "bot.py"]
