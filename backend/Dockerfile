FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Default command runs the API. docker-compose overrides this for the
# reconciliation-worker service to run `rq worker` instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
