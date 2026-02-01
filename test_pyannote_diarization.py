#!/usr/bin/env python3
"""Test Pyannote speaker diarization on AMD ROCm GPU."""

import os
import sys
import time
import torch
import librosa
from pathlib import Path

# Load HF token from .env
from dotenv import load_dotenv
load_dotenv()

HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    print('ERROR: HF_TOKEN not found in .env')
    sys.exit(1)

# Check GPU
print(f'PyTorch: {torch.__version__}')
print(f'ROCm available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'Device: {torch.cuda.get_device_name(0)}')
    device = torch.device('cuda')
else:
    print('WARNING: No GPU, using CPU')
    device = torch.device('cpu')

# Import pyannote
from pyannote.audio import Pipeline

# Test audio path
audio_path = Path('downloads/test_parakeet.wav')
if not audio_path.exists():
    print(f'ERROR: Audio file not found: {audio_path}')
    sys.exit(1)

print(f'\nLoading audio: {audio_path}')
waveform, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
duration = len(waveform) / sample_rate
print(f'Duration: {duration:.1f}s ({duration/60:.1f} min)')

# Load pipeline
print('\nLoading Pyannote speaker-diarization-3.1 pipeline...')
start = time.time()
pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-3.1',
    token=HF_TOKEN
)
pipeline.to(device)
load_time = time.time() - start
print(f'Pipeline loaded in {load_time:.1f}s')

# Prepare audio as dict (avoids torchcodec issues)
audio_dict = {
    'waveform': torch.tensor(waveform).unsqueeze(0),  # (1, samples)
    'sample_rate': sample_rate
}

# Run diarization
print('\nRunning diarization...')
start = time.time()
diarization = pipeline(audio_dict)
diar_time = time.time() - start
print(f'Diarization completed in {diar_time:.1f}s')
print(f'Real-time factor: {diar_time/duration:.2%}')

# Output results
print('\n' + '='*60)
print('SPEAKER SEGMENTS')
print('='*60)
speakers = set()
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speakers.add(speaker)
    print(f'{turn.start:7.2f}s - {turn.end:7.2f}s : {speaker}')

print(f'\nTotal speakers detected: {len(speakers)}')
print(f'Speakers: {sorted(speakers)}')
