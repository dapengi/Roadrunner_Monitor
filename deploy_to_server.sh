#!/usr/bin/env bash
# =====================================================
# Legislative Monitor - Ubuntu Server Deployment Script
# For Ubuntu with NVIDIA GPU (RTX 5060 Ti)
# =====================================================

set -e  # Exit on error

echo "🚀 Legislative Monitor - Server Deployment"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    echo -e "${RED}❌ This script is designed for Ubuntu${NC}"
    echo "Current OS: $(uname -s)"
    exit 1
fi

echo -e "${GREEN}✅ Running on Ubuntu${NC}"
echo ""

# Check for NVIDIA GPU
echo "🔍 Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo -e "${GREEN}✅ NVIDIA GPU detected${NC}"
else
    echo -e "${YELLOW}⚠️  nvidia-smi not found - CUDA drivers may need installation${NC}"
    echo "Would you like to install NVIDIA drivers? (y/n)"
    read -r install_nvidia
    if [ "$install_nvidia" = "y" ]; then
        echo "Installing NVIDIA drivers..."
        sudo apt update
        sudo apt install -y nvidia-driver-535 nvidia-utils-535
        echo "Please reboot and run this script again after reboot"
        exit 0
    fi
fi

echo ""

# Check Python version - Prioritize Python 3.11
echo "📌 Checking Python version..."
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Found Python 3.11: $PYTHON_VERSION${NC}"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    PYTHON_VERSION=$(python3.10 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Found Python 3.10: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3.10 or 3.11 not found!${NC}"
    echo ""
    echo "Please install Python 3.11:"
    echo "  sudo add-apt-repository ppa:deadsnakes/ppa -y"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3.11 python3.11-venv python3.11-dev"
    exit 1
fi

echo ""

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y \
    build-essential \
    ffmpeg \
    git \
    curl \
    wget \
    libsndfile1 \
    sox \
    libsox-dev \
    tesseract-ocr \
    tesseract-ocr-eng

echo -e "${GREEN}✅ System dependencies installed${NC}"
echo ""

# Set up working directory
DEPLOY_DIR="$HOME/legislative_monitor"
echo "📁 Setting up working directory: $DEPLOY_DIR"

if [ -d "$DEPLOY_DIR" ]; then
    echo -e "${YELLOW}⚠️  Directory exists, backing up to ${DEPLOY_DIR}.backup$(date +%Y%m%d_%H%M%S)${NC}"
    mv "$DEPLOY_DIR" "${DEPLOY_DIR}.backup$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

echo -e "${GREEN}✅ Working directory ready${NC}"
echo ""

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

echo -e "${GREEN}✅ Virtual environment created${NC}"
echo ""

# Install PyTorch with CUDA support
echo "🔥 Installing PyTorch with CUDA 13.0..."
pip install torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu130

echo -e "${GREEN}✅ PyTorch with CUDA installed${NC}"
echo ""

# Test PyTorch CUDA
echo "🧪 Testing PyTorch CUDA..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo ""

# Install build dependencies for NeMo
echo "🔧 Installing build dependencies (Cython)..."
pip install Cython
echo -e "${GREEN}✅ Build dependencies installed${NC}"
echo ""

# Install NeMo with ASR support
echo "🤖 Installing NVIDIA NeMo with ASR..."
pip install "nemo_toolkit[asr]==1.23.0"
pip install kaldi-python-io kaldiio

echo -e "${GREEN}✅ NeMo installed${NC}"
echo ""

echo "📋 Installation Summary"
echo "======================="
echo "Python: $($PYTHON_CMD --version)"
echo "PyTorch: $(python -c 'import torch; print(torch.__version__)')"
echo "CUDA Available: $(python -c 'import torch; print(torch.cuda.is_available())')"
if python -c 'import torch; exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    echo "GPU: $(python -c 'import torch; print(torch.cuda.get_device_name(0))')"
fi

echo ""
echo -e "${GREEN}🎉 Server deployment base setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Copy your legislative_monitor.old code to $DEPLOY_DIR"
echo "2. Copy your .env file with credentials"
echo "3. Install remaining dependencies: pip install -r requirements.txt"
echo "4. Test Canary: python test_audio.py your_audio.mp3"
echo ""
