FROM quay.io/astronomer/astro-runtime:8.8.0

USER root

WORKDIR /usr/local/airflow

# Copy requirements files first
COPY requirements.txt packages.txt ./

# Install system dependencies and Python packages
RUN apt-get update && apt-get upgrade -y && \
    if [ -f packages.txt ]; then \
        tr -d '\r' < packages.txt | xargs apt-get install -y --no-install-recommends && \
        rm -rf /var/lib/apt/lists/*; \
    fi && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY dags dags/
COPY include include/
COPY tests tests/

# Create necessary directories
RUN mkdir -p /usr/local/airflow/data/json && \
    chown -R astro:astro /usr/local/airflow/data

# Switch to non-root user for security
USER astro