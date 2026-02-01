#!/usr/bin/env python3
"""Test HuggingFace authentication and model access"""

import os
import sys

print("="*60)
print("HuggingFace Authentication Test")
print("="*60)

# Check 1: HF_TOKEN environment variable
print("\n1. Checking HF_TOKEN environment variable...")
hf_token = os.getenv('HF_TOKEN')
if hf_token:
    print(f"   ✅ HF_TOKEN is set (length: {len(hf_token)})")
    if hf_token.startswith('hf_'):
        print("   ✅ Token format looks correct")
    else:
        print("   ⚠️  Token doesn't start with 'hf_' - might be invalid")
else:
    print("   ❌ HF_TOKEN not set")
    print("   Set it with: export HF_TOKEN='your_token_here'")

# Check 2: huggingface_hub authentication
print("\n2. Checking huggingface_hub authentication...")
try:
    from huggingface_hub import HfFolder
    token = HfFolder.get_token()
    if token:
        print(f"   ✅ Token found in HF cache (length: {len(token)})")
    else:
        print("   ❌ No token in HF cache")
        print("   Login with: huggingface-cli login")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 3: Test model access
print("\n3. Testing pyannote model access...")
try:
    from huggingface_hub import model_info
    
    # Test embedding model
    print("   Testing wespeaker model...")
    info = model_info("pyannote/wespeaker-voxceleb-resnet34-LM")
    print("   ✅ wespeaker-voxceleb-resnet34-LM accessible")
    
    # Test diarization model
    print("   Testing diarization model...")
    info = model_info("pyannote/speaker-diarization-3.1")
    print("   ✅ speaker-diarization-3.1 accessible")
    
    print("\n" + "="*60)
    print("✅ ALL CHECKS PASSED - Ready for enrollment!")
    print("="*60)
    sys.exit(0)
    
except Exception as e:
    error_msg = str(e)
    print(f"   ❌ Error: {error_msg}")
    
    if "403" in error_msg or "Forbidden" in error_msg:
        print("\n" + "="*60)
        print("❌ 403 FORBIDDEN - ACTION REQUIRED")
        print("="*60)
        print("\nYou need to:")
        print("1. Accept model agreements at:")
        print("   https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("   https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM")
        print("\n2. Make sure your token has 'Read' access")
        print("\n3. Set your token:")
        print("   export HF_TOKEN='your_token_here'")
        print("   OR")
        print("   huggingface-cli login")
        
    sys.exit(1)
