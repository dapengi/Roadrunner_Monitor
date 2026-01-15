#!/bin/bash

echo "========================================"
echo "Voice Enrollment - Sherpa + Pyannote"
echo "========================================"
echo ""
echo "Using hybrid approach:"
echo "  • Sherpa-ONNX for speaker diarization"
echo "  • Pyannote for voice embeddings"
echo ""
echo "This avoids all compatibility issues!"
echo ""
read -p "Press Enter to start..."

cd ~/Roadrunner_Monitor
source venv/bin/activate

python3 voice_enrollment/enroll_with_sherpa.py \
    voice_enrollment/audio/House_Appropriation_012425.mp3 \
    --committee HAFC \
    --output voice_enrollment/database/voice_database.json \
    --samples-per-speaker 10

echo ""
echo "========================================"
echo "Done!"
echo "========================================"
