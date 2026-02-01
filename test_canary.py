#!/usr/bin/env python3
"""Test Canary-1b-v2 transcription with GPU acceleration"""

import torch
import time
import librosa
import soundfile as sf
from pathlib import Path

print("=" * 70)
print("🚀 Testing NVIDIA Canary-1b-v2 with GPU Acceleration")
print("=" * 70)

# Check GPU
print(f"\n🔍 GPU Info:")
print(f"   PyTorch: {torch.__version__}")
print(f"   CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA version: {torch.version.cuda}")
    print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# Convert stereo to mono if needed
audio_file = "067a-ac85-4fab-9d40-370df38f07b9.mp3"
mono_file = "067a-ac85-4fab-9d40-370df38f07b9_mono.wav"

print(f"\n🎵 Loading audio: {audio_file}")
audio, sr = librosa.load(audio_file, sr=16000, mono=True)
print(f"   Sample rate: {sr} Hz")
print(f"   Duration: {len(audio) / sr:.1f} seconds")
print(f"   Channels: mono (converted)")

# Save as mono WAV
sf.write(mono_file, audio, sr)
print(f"   Saved mono version: {mono_file}")

# Import Canary
print(f"\n📥 Loading Canary-1b-v2 model...")
import nemo.collections.asr as nemo_asr

start_time = time.time()

# Load Canary model
model = nemo_asr.models.EncDecMultiTaskModel.from_pretrained("nvidia/canary-1b-v2")

# Move to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
model.eval()

load_time = time.time() - start_time
print(f"✅ Model loaded in {load_time:.1f}s on {device}")

# Transcribe
print(f"\n🎙️  Transcribing with Canary-1b-v2...")

start_time = time.time()
transcription = model.transcribe([mono_file], batch_size=1)
transcribe_time = time.time() - start_time

print(f"\n✅ Transcription completed in {transcribe_time:.1f}s")
print(f"\n📝 Result:")
print("=" * 70)
print(transcription[0])
print("=" * 70)

# Show GPU memory usage
if torch.cuda.is_available():
    memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
    memory_reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n💾 GPU Memory Usage:")
    print(f"   Allocated: {memory_allocated:.2f} GB")
    print(f"   Reserved: {memory_reserved:.2f} GB")

print(f"\n🎉 Canary test complete!")
print(f"   Total processing time: {load_time + transcribe_time:.1f}s")
print(f"   Audio duration: {len(audio) / sr:.1f}s")
print(f"   Real-time factor: {(load_time + transcribe_time) / (len(audio) / sr):.2f}x")
