FROM python:3.12-slim

WORKDIR /app

# Installazione di dipendenze necessarie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

CMD ["uvicorn", "rest.server:app", "--host", "0.0.0.0", "--port", "8003"]