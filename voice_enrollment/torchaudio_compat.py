"""
Comprehensive torchaudio compatibility patches for pyannote.audio
Handles incompatibilities between pyannote.audio 3.1.1 and torchaudio 2.9+
"""

import sys
from types import ModuleType
from typing import NamedTuple

# Create AudioMetaData class (was in torchaudio.backend.common)
class AudioMetaData(NamedTuple):
    sample_rate: int
    num_frames: int
    num_channels: int
    bits_per_sample: int
    encoding: str

# Create fake torchaudio.backend module
backend_common = ModuleType('torchaudio.backend.common')
backend_common.AudioMetaData = AudioMetaData

backend = ModuleType('torchaudio.backend')
backend.common = backend_common

# Inject into sys.modules so imports work
sys.modules['torchaudio.backend'] = backend
sys.modules['torchaudio.backend.common'] = backend_common

# Now we can safely import torchaudio
import torchaudio

# Add missing functions
if not hasattr(torchaudio, 'set_audio_backend'):
    torchaudio.set_audio_backend = lambda x: None
    
if not hasattr(torchaudio, 'get_audio_backend'):
    torchaudio.get_audio_backend = lambda: 'soundfile'

print("✓ torchaudio compatibility patches applied")
