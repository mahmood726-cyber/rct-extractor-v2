# RCT Extractor v4.0.6 - Docker Container
# ========================================
# Fully reproducible environment for Research Synthesis Methods compliance
#
# Build: docker build -t rct-extractor:4.0.6 .
# Run:   docker run -v $(pwd)/data:/app/data rct-extractor:4.0.6
# Test:  docker run rct-extractor:4.0.6 pytest tests/ -v

FROM python:3.11-slim-bookworm

LABEL maintainer="RCT Extractor Team"
LABEL version="4.0.6"
LABEL description="Automated effect estimate extraction from clinical trials"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR and language packs
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    # PDF processing
    poppler-utils \
    # Build tools
    build-essential \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -s /bin/bash extractor && \
    chown -R extractor:extractor /app

USER extractor

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.core.enhanced_extractor_v3 import EnhancedExtractor; e = EnhancedExtractor(); print('OK')"

# Default command: run validation
CMD ["python", "regulatory_validation_suite.py"]

# Alternative entrypoints:
# - Run tests: docker run rct-extractor:4.0.6 pytest tests/ -v
# - Interactive: docker run -it rct-extractor:4.0.6 python
# - Validate PDF: docker run -v /path/to/pdfs:/data rct-extractor:4.0.6 python -m src.cli /data/paper.pdf
