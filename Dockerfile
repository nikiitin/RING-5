# Dockerfile for RING-5 Development
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    perl \
    build-essential \
    curl \
    texlive-latex-base \
    texlive-xetex \
    texlive-fonts-recommended \
    cm-super \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m researcher
USER researcher

# Set working directory
WORKDIR /home/researcher/workspace

# Install Python dependencies
COPY --chown=researcher:researcher pyproject.toml README.md .
RUN pip install --default-timeout=100 --no-cache-dir --user ".[dev]"

# Copy the rest of the application
COPY --chown=researcher:researcher . .

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command
CMD ["bash"]
