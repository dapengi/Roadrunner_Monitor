"""
Transcript formatters for client requirements.
Generates JSON, CSV, and TXT outputs from transcription results.
"""

import json
import csv
import io
import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)


class TranscriptFormatter:
    """Formats transcription results into JSON, CSV, and TXT formats."""

    def __init__(self):
        """Initialize the formatter."""
        pass

    def convert_speaker_labels(self, segments: List[Dict]) -> List[Dict]:
        """
        Normalize speaker labels to consistent 'Speaker A', 'Speaker B' format.

        Args:
            segments: List of segments with speaker labels

        Returns:
            Updated segments with speaker_id field
        """
        speaker_mapping = {}
        next_speaker_letter = ord('A')

        for segment in segments:
            original_speaker = segment.get('speaker', 'Unknown')

            if original_speaker not in speaker_mapping:
                # Keep existing 'Speaker X' format or assign new letter
                if original_speaker.startswith('Speaker ') and len(original_speaker) <= 10:
                    speaker_mapping[original_speaker] = original_speaker
                else:
                    speaker_mapping[original_speaker] = f"Speaker {chr(next_speaker_letter)}"
                    next_speaker_letter += 1

            segment['speaker_id'] = speaker_mapping[original_speaker]

        logger.info(f"Mapped {len(speaker_mapping)} speakers: {speaker_mapping}")
        return segments

    def format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in HH:MM:SS format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def create_words_array(self, segments: List[Dict], audio_events: List[Dict] = None) -> List[Dict]:
        """
        Create the words array with spacing elements for JSON output.

        Args:
            segments: List of transcription segments
            audio_events: List of audio events (applause, laughter)

        Returns:
            List of word objects with spacing
        """
        words = []
        audio_events = audio_events or []

        for segment in segments:
            speaker_id = segment.get('speaker_id', 'Speaker A')
            text = segment.get('text', '').strip()
            start_time = segment.get('start', 0.0)
            end_time = segment.get('end', 0.0)

            # Split text into words
            segment_words = text.split()
            if not segment_words:
                continue

            # Calculate approximate timing for each word
            duration = end_time - start_time
            time_per_word = duration / len(segment_words) if len(segment_words) > 0 else 0

            current_time = start_time
            for i, word in enumerate(segment_words):
                word_end = current_time + time_per_word

                # Add word
                words.append({
                    "text": word,
                    "type": "word",
                    "start": round(current_time, 2),
                    "end": round(word_end, 2),
                    "speaker_id": speaker_id
                })

                # Add spacing (except after last word in segment)
                if i < len(segment_words) - 1:
                    words.append({
                        "text": " ",
                        "type": "spacing",
                        "start": round(word_end, 2),
                        "end": round(word_end + 0.04, 2),
                        "speaker_id": speaker_id
                    })

                current_time = word_end

        # Insert audio events
        if audio_events:
            for event in audio_events:
                words.append({
                    "text": f"({event['type']})",
                    "type": "audio_event",
                    "start": event['start'],
                    "end": event['end'],
                    "speaker_id": event.get('speaker_id', 'Speaker A')
                })

            # Sort by start time
            words.sort(key=lambda x: x['start'])

        return words

    def to_json(self, segments: List[Dict], audio_events: List[Dict] = None) -> str:
        """
        Generate JSON format output.

        Format:
        {
          "text": "Full concatenated transcript...",
          "words": [...],
          "audio_events": [...]
        }

        Args:
            segments: List of transcription segments
            audio_events: List of audio events

        Returns:
            JSON string
        """
        # Convert speaker labels
        segments = self.convert_speaker_labels(segments)

        # Create full text
        full_text = " ".join([seg.get('text', '').strip() for seg in segments])

        # Create words array
        words = self.create_words_array(segments, audio_events)

        # Create final JSON structure
        output = {
            "text": full_text,
            "words": words,
            "audio_events": audio_events or []
        }

        return json.dumps(output, indent=2)

    def to_csv(self, segments: List[Dict]) -> str:
        """
        Generate CSV format output.

        Format:
        timestamp,speaker,text
        00:00:05,Speaker A,"Hello everyone..."

        Args:
            segments: List of transcription segments

        Returns:
            CSV string
        """
        # Convert speaker labels
        segments = self.convert_speaker_labels(segments)

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['timestamp', 'speaker', 'text'])

        # Write rows
        for segment in segments:
            timestamp = self.format_timestamp(segment.get('start', 0.0))
            speaker = segment.get('speaker_id', 'Speaker A')
            text = segment.get('text', '').strip()

            writer.writerow([timestamp, speaker, text])

        return output.getvalue()

    def to_txt(self, segments: List[Dict]) -> str:
        """
        Generate speaker-delimited TXT format output.

        Format:
        00:00:05 | Speaker A | Hello everyone, welcome to today's committee hearing.
        00:00:18 | Speaker B | Thank you, Mr. Chairman.

        Args:
            segments: List of transcription segments

        Returns:
            TXT string
        """
        # Convert speaker labels
        segments = self.convert_speaker_labels(segments)

        lines = []
        for segment in segments:
            timestamp = self.format_timestamp(segment.get('start', 0.0))
            speaker = segment.get('speaker_id', 'Speaker A')
            text = segment.get('text', '').strip()

            lines.append(f"{timestamp} | {speaker} | {text}")

        return "\n".join(lines)

    def format_all(self, segments: List[Dict], audio_events: List[Dict] = None) -> Dict[str, str]:
        """
        Generate all three formats at once.

        Args:
            segments: List of transcription segments
            audio_events: List of audio events

        Returns:
            Dictionary with 'json', 'csv', and 'txt' keys
        """
        return {
            'json': self.to_json(segments, audio_events),
            'csv': self.to_csv(segments),
            'txt': self.to_txt(segments)
        }


def test_formatter():
    """Test the formatter with sample data."""

    # Sample transcription segments
    segments = [
        {
            'speaker': 'Speaker A',
            'text': 'Good morning everyone, welcome to today\'s committee hearing.',
            'start': 5.0,
            'end': 10.5
        },
        {
            'speaker': 'Speaker B',
            'text': 'Thank you Mr. Chairman. I would like to address the proposed amendments.',
            'start': 18.0,
            'end': 24.0
        },
        {
            'speaker': 'Speaker A',
            'text': 'Please proceed.',
            'start': 165.0,
            'end': 166.5
        }
    ]

    # Sample audio events
    audio_events = [
        {
            'type': 'applause',
            'start': 25.0,
            'end': 28.0,
            'speaker_id': 'Speaker A'
        }
    ]

    formatter = TranscriptFormatter()

    print("=" * 60)
    print("JSON Output:")
    print("=" * 60)
    print(formatter.to_json(segments, audio_events))
    print("\n")

    print("=" * 60)
    print("CSV Output:")
    print("=" * 60)
    print(formatter.to_csv(segments))
    print("\n")

    print("=" * 60)
    print("TXT Output:")
    print("=" * 60)
    print(formatter.to_txt(segments))


if __name__ == "__main__":
    test_formatter()
