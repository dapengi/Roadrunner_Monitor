#!/usr/bin/env python3
"""Test Pyannote speaker diarization on full audio."""

import os
import sys
import time
import torch
import librosa
from pathlib import Path

# Use CPU for now (GPU JIT compilation too slow on first run)
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from dotenv import load_dotenv
load_dotenv()

HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    print('ERROR: HF_TOKEN not found')
    sys.exit(1)

print(f'PyTorch: {torch.__version__}')
print(f'Using CPU')

from pyannote.audio import Pipeline

audio_path = Path('downloads/test_parakeet.wav')
print(f'\nLoading audio: {audio_path}')
waveform, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
duration = len(waveform) / sample_rate
print(f'Duration: {duration:.1f}s ({duration/60:.1f} min)')

print('\nLoading Pyannote pipeline...')
start = time.time()
pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-3.1',
    token=HF_TOKEN
)
load_time = time.time() - start
print(f'Pipeline loaded in {load_time:.1f}s')

audio_dict = {
    'waveform': torch.tensor(waveform).unsqueeze(0),
    'sample_rate': sample_rate
}

print('\nRunning diarization (this will take a few minutes on CPU)...')
start = time.time()
result = pipeline(audio_dict)
diar_time = time.time() - start
print(f'Diarization completed in {diar_time:.1f}s')
print(f'Real-time factor: {diar_time/duration:.2%}')

diarization = result.speaker_diarization

print('\n' + '='*60)
print('SPEAKER SEGMENTS (first 50)')
print('='*60)
speakers = set()
count = 0
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speakers.add(speaker)
    if count < 50:
        print(f'{turn.start:7.2f}s - {turn.end:7.2f}s : {speaker}')
    count += 1

print(f'\n... {count} total segments')
print(f'\nTotal speakers detected: {len(speakers)}')
print(f'Speakers: {sorted(speakers)}')
