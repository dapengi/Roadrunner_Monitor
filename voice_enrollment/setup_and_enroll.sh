#!/bin/bash

echo "========================================"
echo "Voice Enrollment Setup & Execution"
echo "========================================"
echo ""

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
    echo "❌ HuggingFace token not found"
    echo ""
    echo "You need to:"
    echo "1. Go to https://huggingface.co/settings/tokens"
    echo "2. Create a new token (read access is sufficient)"
    echo "3. Accept the pyannote model agreement at:"
    echo "   https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "4. Run this script again with your token:"
    echo ""
    echo "   export HF_TOKEN='your_token_here'"
    echo "   ./voice_enrollment/setup_and_enroll.sh"
    echo ""
    exit 1
fi

echo "✅ HuggingFace token found"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Run enrollment
echo ""
echo "Starting enrollment process..."
echo ""
echo "Audio file: voice_enrollment/audio/House_Appropriation_012425.mp3"
echo "Committee: HAFC"
echo ""
echo "This will take approximately:"
echo "  - Diarization: 10-15 minutes"
echo "  - Embedding generation: 3-5 minutes"
echo "  - Manual labeling: 5-10 minutes (your input required)"
echo ""
read -p "Press Enter to start..."

python3 voice_enrollment/enroll_from_diarization_fixed.py \
    voice_enrollment/audio/House_Appropriation_012425.mp3 \
    --committee HAFC \
    --output voice_enrollment/database/voice_database.json \
    --min-speakers 8 \
    --max-speakers 20 \
    --samples-per-speaker 10

echo ""
echo "========================================"
echo "Enrollment complete!"
echo "========================================"
