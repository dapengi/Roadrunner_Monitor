#!/usr/bin/env python3
"""Quick GPU test script."""

import torch
import os

print("=" * 50)
print("GPU/ROCm Test")
print("=" * 50)

granite_device = os.environ.get("GRANITE_DEVICE", "not set")
print(f"GRANITE_DEVICE env: {granite_device}")
print(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
print(f"Device count: {torch.cuda.device_count()}")

if torch.cuda.is_available():
    print(f"Device name: {torch.cuda.get_device_name(0)}")

    # Test memory allocation
    print("\nTrying to allocate tensor on GPU...")
    try:
        x = torch.randn(1000, 1000, device="cuda")
        print(f"Successfully allocated {x.numel()} floats on GPU")
        mem_mb = torch.cuda.memory_allocated() / 1024 / 1024
        print(f"GPU memory allocated: {mem_mb:.2f} MB")
        del x
        torch.cuda.empty_cache()
        print("GPU test PASSED")
    except Exception as e:
        print(f"GPU allocation FAILED: {e}")
else:
    print("CUDA not available!")

print("\n" + "=" * 50)
print("Testing Granite import and device resolution...")
print("=" * 50)

try:
    from modules.parallel_transcriber import ParallelTranscriber

    transcriber = ParallelTranscriber(num_workers=1, device="auto")
    print(f"ParallelTranscriber resolved device: {transcriber.device}")

    if transcriber.device == "cuda":
        print("SUCCESS: Granite will use GPU!")
    else:
        print(f"WARNING: Granite will use {transcriber.device}")
except Exception as e:
    print(f"Import error: {e}")
