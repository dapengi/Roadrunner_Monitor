#!/usr/bin/env bash
# =====================================================
# Legislative Monitor (Old) - Environment Setup Script
# =====================================================

set -e  # Exit on error

echo "🚀 Legislative Monitor Setup Script"
echo "===================================="
echo ""

# Find compatible Python version (3.10 or 3.11)
echo "📌 Looking for compatible Python version..."

PYTHON_CMD=""

# Check for python3.10 first (most compatible)
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    PYTHON_VERSION=$(python3.10 --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python 3.10: $PYTHON_VERSION"
# Check for python3.11
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python 3.11: $PYTHON_VERSION"
# Check if default python3 is compatible
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MINOR" -eq 10 ] || [ "$PYTHON_MINOR" -eq 11 ]; then
        PYTHON_CMD="python3"
        echo "✅ Found compatible Python: $PYTHON_VERSION"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: Python 3.10 or 3.11 not found"
    echo ""
    echo "   Please install Python 3.10:"
    echo "   - macOS: brew install python@3.10"
    echo "   - Linux: sudo apt install python3.10-venv"
    echo ""
    echo "   After installation, python3.10 should be available"
    exit 1
fi

echo ""

# Remove old venv if it exists
if [ -d ".venv" ]; then
    echo "🗑️  Removing old virtual environment..."
    rm -rf .venv
fi

# Create new virtual environment
echo "📦 Creating virtual environment with $PYTHON_CMD..."
$PYTHON_CMD -m venv .venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Detect platform and install appropriate PyTorch
echo "🔍 Detecting platform..."
OS_TYPE=$(uname -s)

if [ "$OS_TYPE" = "Darwin" ]; then
    echo "🍎 macOS detected - Installing PyTorch with MPS (Metal) support..."
    echo "   (For CUDA/Linux deployment, PyTorch will be reinstalled on target server)"
    pip install torch==2.1.2 torchaudio==2.1.2
elif [ "$OS_TYPE" = "Linux" ]; then
    echo "🐧 Linux detected - Installing PyTorch with CUDA 12.1..."
    pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
else
    echo "⚠️  Unknown OS: $OS_TYPE - Installing CPU-only PyTorch..."
    pip install torch==2.1.2 torchaudio==2.1.2
fi

# Install remaining requirements
echo "📚 Installing dependencies from requirements.txt..."
# Skip torch/torchaudio since we just installed them
pip install -r requirements.txt --no-deps || true
pip install -r requirements.txt

# Check if .env exists
echo ""
echo "📝 Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo ""
    echo "Please create a .env file from the template:"
    echo "  cp .env.example .env"
    echo ""
    echo "Then edit .env and fill in your credentials:"
    echo "  - OXYLABS_USERNAME and OXYLABS_PASSWORD"
    echo "  - EMAIL_USER and EMAIL_PASSWORD"
    echo "  - HF_TOKEN (from https://huggingface.co/settings/tokens)"
    echo "  - SEAFILE_URL, SEAFILE_USERNAME, SEAFILE_PASSWORD, SEAFILE_LIBRARY_ID"
    echo ""
else
    echo "✅ .env file found"
fi

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p downloads
mkdir -p captions
mkdir -p data

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and fill in your credentials:"
echo "     cp .env.example .env"
echo ""
echo "  2. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  3. Test the configuration:"
echo "     python -c 'from config import validate_config; print(validate_config())'"
echo ""
echo "  4. Run the monitor:"
echo "     python main.py"
echo ""
