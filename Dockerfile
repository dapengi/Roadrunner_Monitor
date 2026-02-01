# =====================================================
# Roadrunner Monitor - Granite Edition
# Optimized for AMD ROCm GPU acceleration
# =====================================================

FROM rocm/pytorch:rocm7.1.1_ubuntu22.04_py3.10_pytorch_release_2.9.1

# Metadata
LABEL maintainer="Roadrunner Monitor"
LABEL description="Legislative meeting transcription with Granite Speech and SpeechBrain"
LABEL version="2.0-granite"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    sox libsox-dev libsndfile1 \
    tesseract-ocr tesseract-ocr-eng \
    build-essential \
    git curl wget \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch nightly for ROCm 7.1 support
RUN pip3 install --no-cache-dir --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/rocm7.1

# Create application directory
WORKDIR /app

# Copy requirements first (for Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create required directories
RUN mkdir -p downloads logs data captions

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command
CMD ["python", "main_hourly.py"]
