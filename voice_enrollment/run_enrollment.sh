#!/bin/bash
cd ~/Roadrunner_Monitor
source venv/bin/activate
python3 voice_enrollment/enroll_from_diarization_fixed.py     voice_enrollment/audio/House_Appropriation_012425.mp3     --committee HAFC     --output voice_enrollment/database/voice_database.json     --min-speakers 8     --max-speakers 20     --samples-per-speaker 10
