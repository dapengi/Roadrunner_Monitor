#!/usr/bin/env python3
"""
Meeting Scanner
Scans directories for caption and audio files, builds meeting inventory.
"""

import os
import re
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


class MeetingScanner:
    """Scans directories to build meeting inventory."""

    def __init__(self, caption_dir: str, audio_dir: str):
        """
        Initialize meeting scanner.

        Args:
            caption_dir: Directory containing caption files
            audio_dir: Directory containing audio files
        """
        self.caption_dir = Path(caption_dir)
        self.audio_dir = Path(audio_dir)

    def scan(self) -> List[Dict]:
        """
        Scan directories and build meeting inventory.

        Returns:
            List of meeting dicts with metadata
        """
        meetings = []

        # Find all caption files
        caption_extensions = ['.vtt', '.srt', '.txt']
        caption_files = []

        if self.caption_dir.exists():
            for ext in caption_extensions:
                caption_files.extend(self.caption_dir.glob(f'*{ext}'))

        # For each caption file, try to find matching audio file
        for caption_file in caption_files:
            basename = caption_file.stem  # Filename without extension

            # Find matching audio file
            audio_file = self._find_audio_file(basename)

            if audio_file:
                # Parse metadata from filename
                metadata = self._parse_filename(basename)

                meeting = {
                    'caption_file': str(caption_file),
                    'audio_file': str(audio_file),
                    **metadata
                }

                meetings.append(meeting)

        return meetings

    def _find_audio_file(self, basename: str) -> Optional[Path]:
        """
        Find audio file matching caption basename.

        Args:
            basename: Caption file basename (without extension)

        Returns:
            Path to audio file or None
        """
        audio_extensions = ['.mp4', '.wav', '.mp3', '.m4a']

        for ext in audio_extensions:
            audio_path = self.audio_dir / f"{basename}{ext}"
            if audio_path.exists():
                return audio_path

        return None

    def _parse_filename(self, filename: str) -> Dict:
        """
        Parse meeting metadata from filename.

        Expected format: YYYYMMDD-{TYPE}-{COMMITTEE}-{STARTTIME}-{ENDTIME}
        Example: 20250115-HOUSE-HAFC-900AM-1200PM

        Args:
            filename: Meeting filename (without extension)

        Returns:
            Dict with parsed metadata
        """
        metadata = {
            'date': None,
            'session_type': None,
            'committee': None,
            'start_time': None,
            'end_time': None,
            'quality_score': 0
        }

        # Pattern: YYYYMMDD-TYPE-COMMITTEE-STARTTIME-ENDTIME
        pattern = r'(\d{8})-([A-Z]+)-([A-Z]+)-(\d+[AP]M)-(\d+[AP]M)'
        match = re.match(pattern, filename)

        if not match:
            # Fallback: try to extract date at least
            date_match = re.search(r'(\d{8})', filename)
            if date_match:
                date_str = date_match.group(1)
                try:
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    metadata['date'] = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            return metadata

        # Extract components
        date_str = match.group(1)
        session_type_raw = match.group(2)
        committee = match.group(3)
        start_time = match.group(4)
        end_time = match.group(5)

        # Parse date
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            metadata['date'] = date_obj.strftime('%Y-%m-%d')
            year = date_obj.year
        except:
            year = None

        # Determine session type
        if session_type_raw == 'IC':
            metadata['session_type'] = 'interim'
        elif session_type_raw in ['HOUSE', 'SENATE']:
            metadata['session_type'] = 'session'
        else:
            metadata['session_type'] = 'unknown'

        metadata['committee'] = committee
        metadata['start_time'] = start_time
        metadata['end_time'] = end_time

        # Calculate quality score
        metadata['quality_score'] = self._calculate_quality_score(
            session_type=metadata['session_type'],
            committee=committee,
            year=year
        )

        return metadata

    def _calculate_quality_score(self, session_type: str, committee: str, year: Optional[int]) -> int:
        """
        Calculate quality score for a meeting (0-100).

        Higher scores indicate better meetings for voice enrollment:
        - Session meetings better than interim (full attendance)
        - Major committees better (more members, more samples)
        - Recent years better (matches current rosters)

        Args:
            session_type: 'session' or 'interim'
            committee: Committee acronym
            year: Meeting year

        Returns:
            Quality score (0-100)
        """
        score = 50  # Base score

        # Session type bonus
        if session_type == 'session':
            score += 30  # Full attendance
        elif session_type == 'interim':
            score += 10  # Partial attendance

        # Major committee bonus
        major_committees = {'HAFC', 'SFC', 'SJC', 'HJC', 'HLLC', 'SLLC'}
        if committee in major_committees:
            score += 20

        # Year bonus (2025 is ideal)
        if year:
            if year == 2025:
                score += 10
            elif year >= 2023:
                score += 5

        return min(score, 100)  # Cap at 100

    def filter_meetings(self, meetings: List[Dict], **criteria) -> List[Dict]:
        """
        Filter meetings by criteria.

        Args:
            meetings: List of meeting dicts
            **criteria: Filter criteria (year, session_type, committees, min_quality)

        Returns:
            Filtered list of meetings
        """
        filtered = meetings

        # Filter by year
        if 'year' in criteria:
            target_year = criteria['year']
            filtered = [
                m for m in filtered
                if m.get('date') and m['date'].startswith(str(target_year))
            ]

        # Filter by session type
        if 'session_type' in criteria:
            target_type = criteria['session_type']
            filtered = [
                m for m in filtered
                if m.get('session_type') == target_type
            ]

        # Filter by committees
        if 'committees' in criteria:
            target_committees = set(criteria['committees'])
            filtered = [
                m for m in filtered
                if m.get('committee') in target_committees
            ]

        # Filter by minimum quality
        if 'min_quality' in criteria:
            min_q = criteria['min_quality']
            filtered = [
                m for m in filtered
                if m.get('quality_score', 0) >= min_q
            ]

        return filtered

    def save_inventory(self, meetings: List[Dict], output_file: str) -> None:
        """
        Save meeting inventory to JSON file.

        Args:
            meetings: List of meeting dicts
            output_file: Output JSON file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        inventory = {
            'scan_date': datetime.now().isoformat(),
            'total_meetings': len(meetings),
            'meetings': meetings
        }

        with open(output_file, 'w') as f:
            json.dump(inventory, f, indent=2)

    def load_inventory(self, inventory_file: str) -> List[Dict]:
        """
        Load meeting inventory from JSON file.

        Args:
            inventory_file: Input JSON file path

        Returns:
            List of meeting dicts
        """
        with open(inventory_file, 'r') as f:
            data = json.load(f)

        return data.get('meetings', [])
