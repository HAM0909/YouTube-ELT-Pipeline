FROM quay.io/astronomer/astro-runtime:8.8.0

WORKDIR /usr/src/app

COPY requirements.txt .
COPY packages.txt .
COPY include/scripts/youtube_elt.py include/scripts/
COPY tests/ tests/

# Install system dependencies
RUN apt-get update && \
    xargs -a packages.txt apt-get install -y && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

USER astro