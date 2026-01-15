#!/usr/bin/env python3
"""
Caption Parser for Voice Enrollment
Parses VTT, SRT, and TXT caption files to extract speaker segments.
"""

import re
from typing import List, Dict, Optional
from pathlib import Path


class CaptionParser:
    """Parser for various caption file formats (VTT, SRT, TXT)."""

    def __init__(self):
        """Initialize caption parser."""
        self.supported_formats = ['.vtt', '.srt', '.txt']

    def parse_file(self, caption_file: str) -> List[Dict]:
        """
        Parse caption file and extract speaker segments.

        Args:
            caption_file: Path to caption file

        Returns:
            List of dicts with keys: speaker, text, start, end

        Raises:
            ValueError: If file format not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(caption_file)

        if not path.exists():
            raise FileNotFoundError(f"Caption file not found: {caption_file}")

        ext = path.suffix.lower()

        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported format: {ext}. Supported: {self.supported_formats}")

        # Parse based on format
        if ext == '.vtt':
            return self._parse_vtt(caption_file)
        elif ext == '.srt':
            return self._parse_srt(caption_file)
        elif ext == '.txt':
            return self._parse_txt(caption_file)

    def _parse_vtt(self, vtt_file: str) -> List[Dict]:
        """Parse WebVTT format."""
        segments = []

        with open(vtt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp line (HH:MM:SS.mmm --> HH:MM:SS.mmm)
            if '-->' in line:
                # Parse timestamps
                match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                if match:
                    start_str = match.group(1)
                    end_str = match.group(2)

                    start_time = self._parse_timestamp(start_str)
                    end_time = self._parse_timestamp(end_str)

                    # Next line(s) should be the caption text
                    i += 1
                    text_lines = []

                    while i < len(lines) and lines[i].strip() != '':
                        text_lines.append(lines[i].strip())
                        i += 1

                    text = ' '.join(text_lines)

                    # Extract speaker from text
                    speaker, clean_text = self._extract_speaker(text)

                    if speaker:
                        segments.append({
                            'speaker': speaker,
                            'text': clean_text,
                            'start': start_time,
                            'end': end_time
                        })

            i += 1

        return segments

    def _parse_srt(self, srt_file: str) -> List[Dict]:
        """Parse SubRip (SRT) format."""
        segments = []

        with open(srt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp line (HH:MM:SS,mmm --> HH:MM:SS,mmm)
            if '-->' in line:
                # Parse timestamps (note: SRT uses comma instead of period)
                match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
                if match:
                    start_str = match.group(1).replace(',', '.')
                    end_str = match.group(2).replace(',', '.')

                    start_time = self._parse_timestamp(start_str)
                    end_time = self._parse_timestamp(end_str)

                    # Next line(s) should be the caption text
                    i += 1
                    text_lines = []

                    while i < len(lines) and lines[i].strip() != '':
                        text_lines.append(lines[i].strip())
                        i += 1

                    text = ' '.join(text_lines)

                    # Extract speaker from text
                    speaker, clean_text = self._extract_speaker(text)

                    if speaker:
                        segments.append({
                            'speaker': speaker,
                            'text': clean_text,
                            'start': start_time,
                            'end': end_time
                        })

            i += 1

        return segments

    def _parse_txt(self, txt_file: str) -> List[Dict]:
        """Parse plain text format with timestamps."""
        segments = []

        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Look for [HH:MM:SS] or similar timestamp patterns
            timestamp_match = re.match(r'\[(\d{2}:\d{2}:\d{2})\](.+)', line)

            if timestamp_match:
                timestamp_str = timestamp_match.group(1) + '.000'
                text = timestamp_match.group(2).strip()

                start_time = self._parse_timestamp(timestamp_str)

                # Extract speaker from text
                speaker, clean_text = self._extract_speaker(text)

                if speaker:
                    # Estimate end time (add 30 seconds as default)
                    end_time = start_time + 30.0

                    segments.append({
                        'speaker': speaker,
                        'text': clean_text,
                        'start': start_time,
                        'end': end_time
                    })

        return segments

    def _parse_timestamp(self, timestamp_str: str) -> float:
        """
        Convert timestamp string to seconds.

        Args:
            timestamp_str: Format like "00:05:23.500"

        Returns:
            Float seconds (e.g., 323.5)
        """
        # Split into hours, minutes, seconds.milliseconds
        parts = timestamp_str.split(':')

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0

        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

        return total_seconds

    def _extract_speaker(self, text: str) -> tuple:
        """
        Extract speaker name from caption text.

        Handles formats like:
        - "SENATOR FIGUEROA: Thank you..."
        - "Rep. Martinez: I agree..."
        - "REPRESENTATIVE JOHNSON: The bill..."

        Args:
            text: Caption text with speaker label

        Returns:
            Tuple of (speaker_name, remaining_text)
        """
        # Pattern: SPEAKER NAME: text
        # Look for pattern like "SENATOR X:" or "REP. X:" at start of line
        patterns = [
            r'^(SENATOR\s+[A-Z]+):(.+)',
            r'^(REPRESENTATIVE\s+[A-Z]+):(.+)',
            r'^(SEN\.\s+[A-Z]+):(.+)',
            r'^(REP\.\s+[A-Z]+):(.+)',
            r'^([A-Z\s]+):(.+)',  # Generic fallback
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                speaker_raw = match.group(1).strip()
                remaining_text = match.group(2).strip()

                # Normalize speaker name
                speaker = self._normalize_speaker_name(speaker_raw)

                return speaker, remaining_text

        return None, text

    def _normalize_speaker_name(self, name: str) -> str:
        """
        Normalize speaker names to consistent format.

        Examples:
        - "SENATOR FIGUEROA" -> "Senator Figueroa"
        - "REPRESENTATIVE MARTINEZ" -> "Representative Martinez"
        - "SEN. JOHNSON" -> "Senator Johnson"
        - "REP SMITH" -> "Representative Smith"

        Args:
            name: Raw speaker name

        Returns:
            Normalized name
        """
        name = name.strip()

        # Replace abbreviations
        name = re.sub(r'\bSEN\.?\b', 'Senator', name, flags=re.IGNORECASE)
        name = re.sub(r'\bREP\.?\b', 'Representative', name, flags=re.IGNORECASE)

        # Title case (Senator/Representative capitalized, last name capitalized)
        words = name.split()
        normalized_words = []

        for word in words:
            if word.lower() in ['senator', 'representative']:
                normalized_words.append(word.capitalize())
            else:
                normalized_words.append(word.capitalize())

        return ' '.join(normalized_words)

    def get_speaker_statistics(self, segments: List[Dict]) -> Dict:
        """
        Get statistics about speakers in segments.

        Args:
            segments: List of segment dicts

        Returns:
            Dict with speaker statistics
        """
        from collections import Counter

        speakers = [seg['speaker'] for seg in segments if seg.get('speaker')]

        speaker_counts = Counter(speakers)

        total_segments = len(segments)
        unique_speakers = len(speaker_counts)

        stats = {
            'total_segments': total_segments,
            'unique_speakers': unique_speakers,
            'speaker_counts': dict(speaker_counts.most_common())
        }

        return stats
