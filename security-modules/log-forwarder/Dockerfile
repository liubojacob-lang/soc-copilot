FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY main.py .

# Create logs directory
RUN mkdir -p /app/logs

# Run
CMD ["python", "-u", "main.py"]
