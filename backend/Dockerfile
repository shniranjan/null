FROM python:3.13-slim

WORKDIR /app

# Install system deps for bcrypt (passlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Ensure data directory exists for SQLite
RUN mkdir -p /opt/data/xcpng-gui/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
