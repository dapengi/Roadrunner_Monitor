"""
Adapter to convert Canary transcription output to segment format.
Bridges NVIDIA Canary-1b-v2 output with existing pipeline formatters.
Includes custom vocabulary correction for NM legislative terms.
"""

import logging
import re
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path for data imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class CanaryAdapter:
    """Adapts Canary output to pipeline segment format with vocabulary correction."""

    def __init__(self, use_vocabulary: bool = True):
        """
        Initialize the adapter.
        
        Args:
            use_vocabulary: Whether to apply vocabulary corrections
        """
        self.use_vocabulary = use_vocabulary
        self.vocab = None
        
        if use_vocabulary:
            try:
                from data.canary_vocabulary import get_canary_vocabulary
                self.vocab = get_canary_vocabulary()
                logger.info("✅ Loaded NM legislative vocabulary for Canary")
            except Exception as e:
                logger.warning(f"Could not load vocabulary: {e}")
                self.use_vocabulary = False

    def parse_canary_output(self, canary_result) -> List[Dict]:
        """
        Parse Canary transcription result into segments with vocabulary correction.
        
        Canary returns a Hypothesis object with:
        - text: Full transcript text
        - y_sequence: Token IDs
        
        Args:
            canary_result: List of Hypothesis objects from Canary
            
        Returns:
            List of segment dictionaries with speaker, text, start, end
        """
        segments = []
        
        if not canary_result:
            logger.warning("Empty Canary result")
            return segments
        
        # Canary returns a list with one result per audio file
        for result in canary_result:
            # Extract full text
            full_text = result.text if hasattr(result, 'text') else str(result)
            
            # Apply vocabulary corrections
            if self.use_vocabulary and self.vocab:
                corrected_text = self.vocab.correct_text(full_text)
                logger.info("Applied NM vocabulary corrections to Canary output")
            else:
                corrected_text = full_text
            
            # For now, create a single segment with the full text
            # In future, could use timestamp info if available
            segments.append({
                'speaker': 'Speaker A',
                'text': corrected_text,
                'start': 0.0,
                'end': 0.0  # Will need actual duration from audio file
            })
            
        logger.info(f"Created {len(segments)} segments from Canary output")
        return segments

    def split_by_sentences(self, text: str, audio_duration: float) -> List[Dict]:
        """
        Split transcript into sentence-based segments.
        Estimates timing based on text length.
        
        Args:
            text: Full transcript text
            audio_duration: Total audio duration in seconds
            
        Returns:
            List of segments with estimated timestamps
        """
        # Apply vocabulary corrections first
        if self.use_vocabulary and self.vocab:
            text = self.vocab.correct_text(text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?:[.!?]+)?\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # Calculate total characters
        total_chars = sum(len(s) for s in sentences)
        
        segments = []
        current_time = 0.0
        
        for sentence in sentences:
            # Estimate duration based on character proportion
            char_ratio = len(sentence) / total_chars if total_chars > 0 else 0
            duration = audio_duration * char_ratio
            
            segments.append({
                'speaker': 'Speaker A',  # Default speaker
                'text': sentence,
                'start': current_time,
                'end': current_time + duration
            })
            
            current_time += duration
        
        logger.info(f"Split into {len(segments)} sentence-based segments")
        return segments
