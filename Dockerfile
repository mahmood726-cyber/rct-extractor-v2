# RCT Extractor - Docker Container
# =================================
# Fully reproducible environment for Research Synthesis Methods compliance
#
# Build: docker build -t rct-extractor .
# Run:   docker run -v $(pwd)/data:/app/data rct-extractor
# Test:  docker run rct-extractor pytest tests/ -v

FROM python:3.11-slim-bookworm

LABEL maintainer="RCT Extractor Team"
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

# Create non-root user for security
RUN useradd -m -s /bin/bash extractor && \
    chown -R extractor:extractor /app

# Copy requirements first for layer caching
COPY --chown=extractor:extractor requirements.txt .

# Install Python dependencies (as non-root user)
USER extractor
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=extractor:extractor . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.core.enhanced_extractor_v3 import EnhancedExtractor; e = EnhancedExtractor(); print('OK')"

# Default command: run API server
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Alternative entrypoints:
# - Run tests: docker run rct-extractor pytest tests/ -v
# - Interactive: docker run -it rct-extractor python
# - CLI: docker run -v /path/to/pdfs:/data rct-extractor python -m src.cli extract /data/paper.pdf
# - Validation: docker run rct-extractor python regulatory_validation_suite.py
