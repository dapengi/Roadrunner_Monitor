#!/usr/bin/env python3
"""
Pyannote-based speaker diarization module.
Replaces SpeechBrain diarization with Pyannote 3.1 for improved accuracy.
Compatible API with SpeechBrain diarizer for drop-in replacement.
"""

import os
import logging
import torch
import librosa
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Lazy load to avoid import errors if pyannote not installed
_pipeline = None
_device = None


def _get_pipeline(hf_token: str, use_gpu: bool = False):
    """Load Pyannote pipeline (cached)."""
    global _pipeline, _device
    
    if _pipeline is not None:
        return _pipeline
    
    from pyannote.audio import Pipeline
    
    logger.info('Loading Pyannote speaker-diarization-3.1 pipeline...')
    
    _pipeline = Pipeline.from_pretrained(
        'pyannote/speaker-diarization-3.1',
        token=hf_token
    )
    
    # Determine device
    if use_gpu and torch.cuda.is_available():
        _device = torch.device('cuda')
        _pipeline.to(_device)
        logger.info(f'Pyannote using GPU: {torch.cuda.get_device_name(0)}')
    else:
        _device = torch.device('cpu')
        logger.info('Pyannote using CPU')
    
    return _pipeline


class PyannoteDiarizer:
    """
    Speaker diarization using Pyannote 3.1.
    API-compatible with SpeechBrainDiarizer for drop-in replacement.
    """
    
    def __init__(
        self,
        device: str = "cpu",
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ):
        """
        Initialize Pyannote diarizer.
        
        Args:
            device: 'cpu' or 'cuda' (GPU has JIT compilation overhead on first run)
            min_speakers: Minimum expected speakers (optional)
            max_speakers: Maximum expected speakers (optional, useful for meetings)
        """
        self.device = device
        self.use_gpu = (device == "cuda")
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.hf_token = None
        self._pipeline = None
    
    def _ensure_token(self):
        """Get HuggingFace token."""
        if self.hf_token is None:
            self.hf_token = os.getenv('HF_TOKEN')
        if not self.hf_token:
            raise ValueError(
                'HuggingFace token required. Set HF_TOKEN env var.'
            )
        return self.hf_token
    
    def diarize(self, audio_path: str) -> List[Dict]:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            List of dicts with 'speaker', 'start', 'end' keys
            (same format as SpeechBrainDiarizer)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        token = self._ensure_token()
        pipeline = _get_pipeline(token, self.use_gpu)
        
        # Load audio
        logger.info(f'Loading audio: {audio_path}')
        waveform, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(waveform) / sample_rate
        logger.info(f'Audio duration: {duration:.1f}s ({duration/60:.1f} min)')
        
        # Prepare audio dict (avoids torchcodec issues)
        audio_dict = {
            'waveform': torch.tensor(waveform).unsqueeze(0),
            'sample_rate': sample_rate
        }
        
        # Run diarization with optional speaker constraints
        logger.info('Running Pyannote diarization...')
        pipeline_kwargs = {}
        if self.min_speakers is not None:
            pipeline_kwargs['min_speakers'] = self.min_speakers
        if self.max_speakers is not None:
            pipeline_kwargs['max_speakers'] = self.max_speakers
        
        if pipeline_kwargs:
            logger.info(f'Speaker constraints: {pipeline_kwargs}')
            result = pipeline(audio_dict, **pipeline_kwargs)
        else:
            result = pipeline(audio_dict)
        
        # Extract segments in SpeechBrain-compatible format
        diarization = result.speaker_diarization
        segments = []
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'speaker': speaker,
                'start': turn.start,
                'end': turn.end
            })
        
        # Get unique speakers
        speakers = set(seg['speaker'] for seg in segments)
        logger.info(f'Detected {len(speakers)} speakers, {len(segments)} segments')
        
        return segments
    
    def diarize_with_transcript(
        self,
        audio_path: str,
        transcript: str
    ) -> List[Dict]:
        """
        Perform diarization and assign text to segments.
        
        Args:
            audio_path: Path to audio file
            transcript: Full transcript text
        
        Returns:
            List of dicts with 'speaker', 'start', 'end', 'text' keys
        """
        segments = self.diarize(audio_path)
        
        if not segments or not transcript:
            return segments
        
        # Split transcript proportionally
        total_duration = sum(seg['end'] - seg['start'] for seg in segments)
        if total_duration <= 0:
            return segments
        
        words = transcript.split()
        total_words = len(words)
        word_idx = 0
        
        for seg in segments:
            seg_duration = seg['end'] - seg['start']
            seg_word_count = int((seg_duration / total_duration) * total_words)
            seg_word_count = max(1, min(seg_word_count, total_words - word_idx))
            
            seg_words = words[word_idx:word_idx + seg_word_count]
            seg['text'] = ' '.join(seg_words)
            word_idx += seg_word_count
        
        # Assign remaining words to last segment
        if word_idx < total_words and segments:
            remaining = ' '.join(words[word_idx:])
            segments[-1]['text'] = segments[-1].get('text', '') + ' ' + remaining
        
        return segments


if __name__ == '__main__':
    # Test
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print('Usage: python pyannote_diarization.py <audio_file>')
        sys.exit(1)
    
    audio_file = sys.argv[1]
    diarizer = PyannoteDiarizer(device="cpu")
    segments = diarizer.diarize(audio_file)
    
    print(f'\nFirst 20 segments:')
    for seg in segments[:20]:
        print(f"{seg['start']:7.2f}s - {seg['end']:7.2f}s : {seg['speaker']}")
    
    speakers = set(seg['speaker'] for seg in segments)
    print(f'\nTotal: {len(segments)} segments, {len(speakers)} speakers')
