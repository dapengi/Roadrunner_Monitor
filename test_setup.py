#!/usr/bin/env python3
"""
Test script to verify Legislative Monitor setup is correct.
Run this after completing setup.sh and configuring .env
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required packages can be imported."""
    print("🔍 Testing imports...")
    failures = []

    packages = [
        ('torch', 'PyTorch'),
        ('faster_whisper', 'Faster Whisper'),
        ('sherpa_onnx', 'Sherpa ONNX'),
        ('numpy', 'NumPy'),
        ('requests', 'Requests'),
        ('bs4', 'BeautifulSoup4'),
        ('yt_dlp', 'yt-dlp'),
        ('docx', 'python-docx'),
        ('schedule', 'schedule'),
    ]

    for package, name in packages:
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name}: {e}")
            failures.append(name)

    if failures:
        print(f"\n❌ Failed to import: {', '.join(failures)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("✅ All imports successful\n")
    return True


def test_config():
    """Test that configuration is valid."""
    print("🔍 Testing configuration...")

    try:
        from config import validate_config, get_config_summary

        errors = validate_config()
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease check your .env file")
            return False

        print("✅ Configuration is valid")

        summary = get_config_summary()
        print("\n📋 Configuration Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False


def test_proxy():
    """Test Oxylabs proxy connection."""
    print("\n🔍 Testing Oxylabs proxy connection...")

    try:
        from modules.proxy_manager import ProxyManager

        proxy_manager = ProxyManager()
        success = proxy_manager.test_proxy_connection(max_retries=2)

        if success:
            print("✅ Proxy connection successful")
            config = proxy_manager.proxy_config
            print(f"  Proxy IP: {config.get('current_ip', 'Unknown')}")
            print(f"  Location: {config.get('country', 'Unknown')}")
            return True
        else:
            print("❌ Proxy connection failed")
            print("  Check your OXYLABS_USERNAME and OXYLABS_PASSWORD in .env")
            return False

    except Exception as e:
        print(f"❌ Error testing proxy: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_seafile():
    """Test Seafile connection."""
    print("\n🔍 Testing Seafile connection...")

    try:
        from modules.seafile_client import SeafileClient

        client = SeafileClient()

        # Try to list root directory
        result = client.list_dir("/")

        if result is not None:
            print("✅ Seafile connection successful")
            print(f"  Found {len(result)} items in root directory")
            return True
        else:
            print("❌ Seafile connection failed")
            print("  Check your SEAFILE_* variables in .env")
            return False

    except Exception as e:
        print(f"❌ Error testing Seafile: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gpu():
    """Test GPU availability."""
    print("\n🔍 Testing GPU availability...")

    try:
        import torch

        if torch.cuda.is_available():
            print("✅ CUDA GPU available")
            print(f"  Device: {torch.cuda.get_device_name(0)}")
            print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return True
        else:
            print("⚠️  No CUDA GPU found - will use CPU")
            print("  This is OK but transcription will be slower")
            return True

    except Exception as e:
        print(f"❌ Error checking GPU: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Legislative Monitor - Setup Verification")
    print("=" * 60)
    print()

    results = {
        'Imports': test_imports(),
        'Configuration': test_config(),
        'Proxy': test_proxy(),
        'Seafile': test_seafile(),
        'GPU': test_gpu(),
    }

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20s} {status}")

    print()

    all_passed = all(results.values())

    if all_passed:
        print("🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Run a test meeting: python process_single_meeting.py")
        print("  2. Or start monitoring: python main.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
