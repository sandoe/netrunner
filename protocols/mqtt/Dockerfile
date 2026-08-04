FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Command should be specified in docker-compose depending on if it's pub or sub
CMD ["python", "test-pub.py"]
