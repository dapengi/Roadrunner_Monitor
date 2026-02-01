#!/bin/bash

echo "========================================"
echo "Voice Enrollment - NeMo TitaNet"
echo "========================================"
echo ""
echo "Using hybrid approach:"
echo "  • Sherpa-ONNX for speaker diarization"
echo "  • NeMo TitaNet for voice embeddings"
echo ""
echo "NeMo TitaNet provides superior accuracy"
echo "for distinguishing between legislators!"
echo ""
read -p "Press Enter to start..."

cd ~/Roadrunner_Monitor
source venv/bin/activate

python3 voice_enrollment/enroll_with_nemo.py \
    voice_enrollment/audio/House_Appropriation_012425.mp3 \
    --committee HAFC \
    --output voice_enrollment/database/voice_database.json \
    --samples-per-speaker 10

echo ""
echo "========================================"
echo "Done!"
echo "========================================"
