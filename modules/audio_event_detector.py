"""
Audio event detection for legislative transcripts.
Detects applause, laughter, and other audio events using PANNs inference.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import panns_inference
try:
    from panns_inference import AudioTagging, SoundEventDetection, labels
    PANNS_AVAILABLE = True
    logger.info("PANNs audio tagging models available")
except ImportError:
    PANNS_AVAILABLE = False
    logger.warning("PANNs not available - audio event detection will be disabled")


class AudioEventDetector:
    """Detects audio events like applause and laughter in audio files."""

    def __init__(self, sample_rate: int = 32000):
        """
        Initialize the audio event detector.

        Args:
            sample_rate: Sample rate for audio processing (PANNs uses 32kHz)
        """
        self.sample_rate = sample_rate
        self.model = None
        self.sed_model = None

        # Events we care about
        self.target_events = {
            'Applause': 'applause',
            'Laughter': 'laughing',
            'Clapping': 'applause'
        }

    def load_models(self):
        """Load PANNs models for audio event detection."""
        if not PANNS_AVAILABLE:
            logger.warning("PANNs not available - skipping model load")
            return False

        try:
            logger.info("Loading PANNs audio tagging model...")
            self.model = AudioTagging(checkpoint_path=None, device='cpu')

            logger.info("Loading PANNs sound event detection model...")
            self.sed_model = SoundEventDetection(checkpoint_path=None, device='cpu')

            logger.info("Audio event detection models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load audio event detection models: {e}")
            return False

    def detect_events(self, audio_path: str, threshold: float = 0.3) -> List[Dict]:
        """
        Detect audio events in an audio file.

        Args:
            audio_path: Path to audio file (WAV or MP3)
            threshold: Confidence threshold for event detection (0-1)

        Returns:
            List of detected events with timestamps
        """
        if not PANNS_AVAILABLE:
            logger.info("PANNs not available - returning empty events list")
            return []

        try:
            # Load models if not already loaded
            if self.model is None:
                if not self.load_models():
                    return []

            # Load audio file
            import librosa
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

            logger.info(f"Detecting audio events in {audio_path} (duration: {len(audio)/sr:.1f}s)")

            # Ensure audio is in the correct shape for PANNs (needs to be 2D: batch_size x samples)
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]  # Add batch dimension

            # Perform sound event detection
            framewise_output = self.sed_model.inference(audio)

            # Process results
            events = []
            event_labels = labels

            # Analyze framewise output (10Hz resolution, 0.1s per frame)
            frame_duration = 0.1  # seconds per frame
            current_event = None

            for frame_idx, frame_probs in enumerate(framewise_output):
                timestamp = frame_idx * frame_duration

                # Check each target event
                for panns_label, our_label in self.target_events.items():
                    if panns_label in event_labels:
                        label_idx = event_labels.index(panns_label)
                        prob = frame_probs[label_idx]

                        if prob > threshold:
                            # Event detected
                            if current_event is None or current_event['type'] != our_label:
                                # Start new event
                                if current_event:
                                    events.append(current_event)

                                current_event = {
                                    'type': our_label,
                                    'start': timestamp,
                                    'end': timestamp + frame_duration,
                                    'confidence': float(prob)
                                }
                            else:
                                # Extend current event
                                current_event['end'] = timestamp + frame_duration
                                current_event['confidence'] = max(current_event['confidence'], float(prob))

            # Add final event if exists
            if current_event:
                events.append(current_event)

            # Filter out very short events (< 0.5 seconds)
            events = [e for e in events if (e['end'] - e['start']) >= 0.5]

            # Merge nearby events of same type (within 1 second)
            events = self._merge_nearby_events(events, gap_threshold=1.0)

            logger.info(f"Detected {len(events)} audio events: {[e['type'] for e in events]}")
            return events

        except Exception as e:
            logger.error(f"Error detecting audio events: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _merge_nearby_events(self, events: List[Dict], gap_threshold: float = 1.0) -> List[Dict]:
        """
        Merge nearby events of the same type.

        Args:
            events: List of events
            gap_threshold: Maximum gap in seconds to merge

        Returns:
            Merged events list
        """
        if not events:
            return []

        # Sort by start time
        events.sort(key=lambda x: x['start'])

        merged = []
        current = events[0].copy()

        for event in events[1:]:
            # Check if same type and close enough
            if (event['type'] == current['type'] and
                event['start'] - current['end'] < gap_threshold):
                # Merge
                current['end'] = event['end']
                current['confidence'] = max(current['confidence'], event['confidence'])
            else:
                # Add current and start new
                merged.append(current)
                current = event.copy()

        # Add final event
        merged.append(current)

        return merged

    def detect_events_simple(self, audio_path: str) -> List[Dict]:
        """
        Simplified detection - just detect applause and laughter with good defaults.

        Args:
            audio_path: Path to audio file

        Returns:
            List of events (applause, laughing)
        """
        return self.detect_events(audio_path, threshold=0.3)


def test_detector():
    """Test the audio event detector."""
    detector = AudioEventDetector()

    # This is just a test - would need actual audio file
    print("Audio Event Detector initialized")
    print(f"PANNs available: {PANNS_AVAILABLE}")
    print(f"Target events: {detector.target_events}")

    if PANNS_AVAILABLE:
        print("\nTo test with real audio:")
        print("  detector = AudioEventDetector()")
        print("  events = detector.detect_events('path/to/audio.mp3')")
        print("  print(events)")


if __name__ == "__main__":
    test_detector()
