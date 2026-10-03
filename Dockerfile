FROM python:3.11-slim

LABEL maintainer="Ratanazen <Rtnaeam611@gmail.com>"
LABEL description="Hadoop & PySpark Log File Analysis Dashboard"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Run data analysis to generate all deliverables
RUN python run_analysis.py && python export_report.py

# Expose web server port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Start web server
CMD ["python", "serve.py", "8080"]
