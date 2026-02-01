#!/bin/bash
set -e

echo "=========================================="
echo "Roadrunner Monitor - Granite Edition"
echo "=========================================="

# Check for .env file
if [ ! -f /app/.env ]; then
    echo "WARNING: No .env file found at /app/.env"
    echo "Make sure to mount your .env file"
fi

# Validate configuration
echo "Validating configuration..."
python -c "from config import validate_config; errors = validate_config(); print('Config OK' if not errors else errors)"

# Check ROCm GPU availability
echo ""
echo "Checking GPU availability..."
python -c "
import torch
if torch.cuda.is_available():
    print(f'GPU available: {torch.cuda.get_device_name(0)}')
    print(f'ROCm/CUDA version: {torch.version.cuda}')
else:
    print('No GPU detected - will use CPU')
"

echo ""
echo "Starting application..."
echo "=========================================="

# Execute the command passed to docker run
exec "$@"
