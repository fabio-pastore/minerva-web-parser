FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.org/simple/

COPY . .
CMD ["uvicorn", "src.frontend:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]