#!/usr/bin/env python3
"""Test Pyannote speaker diarization on CPU."""

import os
import sys
import time
import torch
import librosa
from pathlib import Path

# Force CPU
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from dotenv import load_dotenv
load_dotenv()

HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    print('ERROR: HF_TOKEN not found')
    sys.exit(1)

print(f'PyTorch: {torch.__version__}')
print(f'Using CPU (GPU disabled for testing)')
device = torch.device('cpu')

from pyannote.audio import Pipeline

# Use shorter test file
audio_path = Path('downloads/test_60s.wav')
if not audio_path.exists():
    audio_path = Path('downloads/test_parakeet.wav')

print(f'\nLoading audio: {audio_path}')
waveform, sample_rate = librosa.load(audio_path, sr=16000, mono=True)

# Limit to first 60 seconds for quick test
max_samples = 60 * sample_rate
if len(waveform) > max_samples:
    waveform = waveform[:max_samples]
    print(f'Trimmed to 60s for quick test')

duration = len(waveform) / sample_rate
print(f'Duration: {duration:.1f}s')

print('\nLoading Pyannote pipeline...')
start = time.time()
pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-3.1',
    token=HF_TOKEN
)
# Keep on CPU
load_time = time.time() - start
print(f'Pipeline loaded in {load_time:.1f}s')

audio_dict = {
    'waveform': torch.tensor(waveform).unsqueeze(0),
    'sample_rate': sample_rate
}

print('\nRunning diarization on CPU...')
start = time.time()
diarization = pipeline(audio_dict)
diar_time = time.time() - start
print(f'Diarization completed in {diar_time:.1f}s')
print(f'Real-time factor: {diar_time/duration:.2%}')

print('\n' + '='*60)
print('SPEAKER SEGMENTS')
print('='*60)
speakers = set()
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speakers.add(speaker)
    print(f'{turn.start:7.2f}s - {turn.end:7.2f}s : {speaker}')

print(f'\nTotal speakers detected: {len(speakers)}')
