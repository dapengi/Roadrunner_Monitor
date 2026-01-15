#!/usr/bin/env python3
"""
Validation script to check if voice enrollment system is ready to use.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_directories():
    """Check if required directories exist."""
    print("\n📁 Checking directories...")

    required_dirs = [
        'voice_enrollment/captions',
        'voice_enrollment/audio',
        'voice_enrollment/database',
        'voice_enrollment/reports',
        'voice_enrollment/temp'
    ]

    all_exist = True
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {dir_path}")
        if not exists:
            all_exist = False

    return all_exist


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n📦 Checking dependencies...")

    required_packages = {
        'pyannote.audio': 'pyannote-audio',
        'librosa': 'librosa',
        'numpy': 'numpy',
        'torch': 'torch'
    }

    all_installed = True
    for package, pip_name in required_packages.items():
        try:
            __import__(package.replace('.', '/'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (install: pip install {pip_name})")
            all_installed = False

    return all_installed


def check_pyannote_model():
    """Check if Pyannote model can be loaded."""
    print("\n🤖 Checking Pyannote model...")

    try:
        from pyannote.audio import Inference
        model = Inference('pyannote/wespeaker-voxceleb-resnet34-LM')
        print("   ✅ Model loaded successfully")
        return True
    except Exception as e:
        print(f"   ❌ Model loading failed: {e}")
        return False


def check_committee_rosters():
    """Check if committee rosters are available."""
    print("\n👥 Checking committee rosters...")

    try:
        from data.committee_rosters import COMMITTEE_ROSTERS

        if not COMMITTEE_ROSTERS:
            print("   ❌ COMMITTEE_ROSTERS is empty")
            return False

        print(f"   ✅ Found {len(COMMITTEE_ROSTERS)} committees")

        # Show sample
        total_members = sum(len(members) for members in COMMITTEE_ROSTERS.values())
        print(f"   ℹ️  Total legislators: {total_members}")

        return True
    except ImportError:
        print("   ❌ Could not import committee rosters from data/committee_rosters.py")
        return False


def check_files():
    """Check if caption and audio files are present."""
    print("\n📄 Checking for caption and audio files...")

    caption_dir = Path('voice_enrollment/captions')
    audio_dir = Path('voice_enrollment/audio')

    caption_files = []
    audio_files = []

    if caption_dir.exists():
        caption_files = list(caption_dir.glob('*.vtt')) + \
                       list(caption_dir.glob('*.srt')) + \
                       list(caption_dir.glob('*.txt'))

    if audio_dir.exists():
        audio_files = list(audio_dir.glob('*.mp4')) + \
                     list(audio_dir.glob('*.wav')) + \
                     list(audio_dir.glob('*.mp3'))

    print(f"   Caption files: {len(caption_files)}")
    print(f"   Audio files: {len(audio_files)}")

    if len(caption_files) == 0 or len(audio_files) == 0:
        print("   ⚠️  No files found. Add files before running enrollment.")
        print(f"   📁 Captions: {caption_dir.absolute()}")
        print(f"   📁 Audio: {audio_dir.absolute()}")
        return False

    # Check for matching pairs
    caption_basenames = {f.stem for f in caption_files}
    audio_basenames = {f.stem for f in audio_files}

    matching = caption_basenames & audio_basenames
    print(f"   ✅ Matching pairs: {len(matching)}")

    if len(matching) == 0:
        print("   ❌ No matching caption/audio pairs found!")
        print("   ℹ️  Ensure filenames match (except extension)")
        return False

    return True


def check_scripts():
    """Check if main scripts are executable."""
    print("\n🔧 Checking scripts...")

    scripts = [
        'voice_enrollment/caption_parser.py',
        'voice_enrollment/meeting_scanner.py',
        'voice_enrollment/voice_embedder.py',
        'voice_enrollment/meeting_selector.py',
        'voice_enrollment/enroll_voices.py'
    ]

    all_exist = True
    for script in scripts:
        exists = Path(script).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {script}")
        if not exists:
            all_exist = False

    return all_exist


def main():
    """Run all validation checks."""
    print("\n" + "=" * 80)
    print("🔍 VOICE ENROLLMENT SYSTEM - VALIDATION")
    print("=" * 80)

    results = {
        'Directories': check_directories(),
        'Dependencies': check_dependencies(),
        'Pyannote Model': check_pyannote_model(),
        'Committee Rosters': check_committee_rosters(),
        'Files': check_files(),
        'Scripts': check_scripts()
    }

    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {check}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)

    if all_passed:
        print("✅ ALL CHECKS PASSED - System ready for enrollment!")
        print("\n🚀 Next steps:")
        print("   1. Add caption and audio files to voice_enrollment/captions/ and voice_enrollment/audio/")
        print("   2. Run: python3 voice_enrollment/meeting_selector.py")
        print("   3. Run: python3 voice_enrollment/enroll_voices.py")
    else:
        print("❌ SOME CHECKS FAILED - Please fix issues before proceeding")
        print("\n🔧 Common fixes:")
        if not results['Dependencies']:
            print("   - Install dependencies: pip install pyannote-audio librosa torch numpy")
        if not results['Pyannote Model']:
            print("   - Pyannote model will auto-download on first use")
        if not results['Files']:
            print("   - Add caption/audio files to voice_enrollment directories")

    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
