#!/usr/bin/env python3
"""
Meeting Selector with Auto-Suggest
Scans directories, filters 2025 session meetings, and provides interactive selection.
"""

import os
import sys
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_enrollment.meeting_scanner import MeetingScanner


class MeetingSelector:
    """Interactive meeting selector with auto-suggest functionality."""

    def __init__(self, caption_dir: str, audio_dir: str):
        """
        Initialize meeting selector.

        Args:
            caption_dir: Directory containing caption files
            audio_dir: Directory containing audio files
        """
        self.caption_dir = caption_dir
        self.audio_dir = audio_dir
        self.scanner = MeetingScanner(caption_dir, audio_dir)
        self.selected_meetings = []

    def scan_and_filter(self, year: int = 2025, session_type: str = 'session') -> List[Dict]:
        """
        Scan directories and filter for target meetings.

        Args:
            year: Target year (default: 2025)
            session_type: 'session' or 'interim' (default: session)

        Returns:
            List of filtered meetings sorted by quality score
        """
        print(f"\n🔍 Scanning directories for {year} {session_type} meetings...")

        # Scan all meetings
        all_meetings = self.scanner.scan()
        print(f"   Found {len(all_meetings)} total meetings")

        # Filter by criteria
        filtered = self.scanner.filter_meetings(
            all_meetings,
            year=year,
            session_type=session_type,
            min_quality=50  # Only reasonably good quality meetings
        )

        print(f"   Filtered to {len(filtered)} {year} {session_type} meetings")

        # Sort by quality score (highest first)
        filtered.sort(key=lambda m: m.get('quality_score', 0), reverse=True)

        return filtered

    def suggest_best_meetings(self, meetings: List[Dict], count: int = 10) -> List[Dict]:
        """
        Suggest the best meetings for voice enrollment.

        Prioritizes:
        1. Major committees (HAFC, SFC, SJC, HJC)
        2. Session meetings (full attendance)
        3. Longer duration (more voice samples)
        4. Recent dates (2025)

        Args:
            meetings: List of candidate meetings
            count: Number of suggestions to return

        Returns:
            Top N suggested meetings
        """
        # Boost scores for major committees
        major_committees = {'HAFC', 'SFC', 'SJC', 'HJC', 'HLLC', 'SLLC'}

        for meeting in meetings:
            committee = meeting.get('committee', '')
            if committee in major_committees:
                meeting['quality_score'] = meeting.get('quality_score', 0) + 20

        # Re-sort with boosted scores
        meetings.sort(key=lambda m: m.get('quality_score', 0), reverse=True)

        # Return top N
        return meetings[:count]

    def display_suggestions(self, suggestions: List[Dict]) -> None:
        """
        Display suggested meetings in a user-friendly format.

        Args:
            suggestions: List of suggested meetings
        """
        print("\n" + "=" * 80)
        print("📋 SUGGESTED MEETINGS FOR VOICE ENROLLMENT")
        print("=" * 80)

        if not suggestions:
            print("\n❌ No meetings found matching criteria.")
            return

        for idx, meeting in enumerate(suggestions, 1):
            # Extract metadata
            date = meeting.get('date', 'Unknown')
            session_type = meeting.get('session_type', 'Unknown')
            committee = meeting.get('committee', 'Unknown')
            start_time = meeting.get('start_time', '?')
            end_time = meeting.get('end_time', '?')
            quality = meeting.get('quality_score', 0)

            # Calculate duration (approximate from times if available)
            duration = "Unknown"
            if start_time != '?' and end_time != '?':
                try:
                    # Parse times like "900AM" and "1200PM"
                    start_hr = int(start_time[:-2])
                    end_hr = int(end_time[:-2])
                    if 'PM' in end_time and end_hr != 12:
                        end_hr += 12
                    if 'PM' in start_time and start_hr != 12:
                        start_hr += 12
                    duration_hrs = end_hr - start_hr
                    duration = f"{duration_hrs}h" if duration_hrs > 0 else "Unknown"
                except:
                    pass

            # Display meeting info
            print(f"\n{idx}. [{quality}/100] {date} - {session_type.upper()} - {committee}")
            print(f"   Time: {start_time} to {end_time} ({duration})")
            print(f"   Caption: {os.path.basename(meeting.get('caption_file', 'N/A'))}")
            print(f"   Audio: {os.path.basename(meeting.get('audio_file', 'N/A'))}")

            # Add quality indicators
            indicators = []
            if session_type.lower() == 'session':
                indicators.append("⭐ Full Attendance")
            if committee in {'HAFC', 'SFC', 'SJC', 'HJC'}:
                indicators.append("🏛️ Major Committee")
            if quality >= 80:
                indicators.append("✨ High Quality")

            if indicators:
                print(f"   {' | '.join(indicators)}")

        print("\n" + "=" * 80)

    def interactive_selection(self, suggestions: List[Dict], max_selections: int = 10) -> List[Dict]:
        """
        Interactive interface for selecting meetings.

        Args:
            suggestions: List of suggested meetings
            max_selections: Maximum number of meetings to select

        Returns:
            List of selected meetings
        """
        if not suggestions:
            print("\n❌ No meetings available for selection.")
            return []

        print(f"\n📝 SELECT MEETINGS FOR ENROLLMENT (Max: {max_selections})")
        print("-" * 80)
        print("Options:")
        print("  - Enter numbers (e.g., '1,3,5' or '1-5')")
        print("  - Enter 'all' to select all suggested meetings")
        print("  - Enter 'top5' or 'top10' to select top N")
        print("  - Enter 'done' when finished")
        print("-" * 80)

        selected = []

        while True:
            user_input = input("\nYour selection: ").strip().lower()

            if user_input == 'done':
                break
            elif user_input == 'all':
                selected = suggestions[:max_selections]
                print(f"✓ Selected all {len(selected)} meetings")
                break
            elif user_input.startswith('top'):
                try:
                    n = int(user_input.replace('top', ''))
                    selected = suggestions[:min(n, max_selections)]
                    print(f"✓ Selected top {len(selected)} meetings")
                    break
                except:
                    print("❌ Invalid format. Use 'top5' or 'top10'")
            else:
                # Parse number ranges and individual numbers
                try:
                    indices = self._parse_selection(user_input, len(suggestions))
                    selected = [suggestions[i] for i in indices if i < len(suggestions)]

                    if len(selected) > max_selections:
                        print(f"⚠️  Too many selections. Limited to first {max_selections}")
                        selected = selected[:max_selections]

                    print(f"✓ Selected {len(selected)} meetings")
                    break
                except Exception as e:
                    print(f"❌ Invalid selection: {e}")

        return selected

    def _parse_selection(self, input_str: str, max_idx: int) -> List[int]:
        """
        Parse user selection string into list of indices.

        Args:
            input_str: User input (e.g., "1,3,5" or "1-5")
            max_idx: Maximum valid index

        Returns:
            List of zero-based indices
        """
        indices = []
        parts = input_str.split(',')

        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range (e.g., "1-5")
                start, end = part.split('-')
                start_idx = int(start) - 1  # Convert to 0-based
                end_idx = int(end) - 1
                indices.extend(range(start_idx, end_idx + 1))
            else:
                # Single number
                indices.append(int(part) - 1)  # Convert to 0-based

        # Remove duplicates and sort
        indices = sorted(set(indices))

        # Validate range
        if any(i < 0 or i >= max_idx for i in indices):
            raise ValueError(f"Numbers must be between 1 and {max_idx}")

        return indices

    def save_selection(self, selected_meetings: List[Dict], output_file: str) -> None:
        """
        Save selected meetings to JSON file.

        Args:
            selected_meetings: List of selected meetings
            output_file: Output JSON file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare selection data
        selection_data = {
            'selection_date': datetime.now().isoformat(),
            'total_meetings': len(selected_meetings),
            'meetings': selected_meetings
        }

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(selection_data, f, indent=2)

        print(f"\n✅ Selection saved to: {output_file}")

    def run_interactive_session(self, year: int = 2025, max_selections: int = 10) -> List[Dict]:
        """
        Run complete interactive selection session.

        Args:
            year: Target year for meetings
            max_selections: Maximum number of meetings to select

        Returns:
            List of selected meetings
        """
        print("\n" + "=" * 80)
        print("🎙️  VOICE ENROLLMENT - MEETING SELECTOR")
        print("=" * 80)

        # Step 1: Scan and filter
        meetings = self.scan_and_filter(year=year, session_type='session')

        if not meetings:
            print("\n❌ No meetings found. Please add caption and audio files to:")
            print(f"   Captions: {self.caption_dir}")
            print(f"   Audio: {self.audio_dir}")
            return []

        # Step 2: Suggest best meetings
        suggestions = self.suggest_best_meetings(meetings, count=max_selections)

        # Step 3: Display suggestions
        self.display_suggestions(suggestions)

        # Step 4: Interactive selection
        selected = self.interactive_selection(suggestions, max_selections)

        if selected:
            print(f"\n✅ {len(selected)} meetings selected for enrollment")

            # Show summary
            print("\n📊 SELECTION SUMMARY:")
            committees = set(m.get('committee', 'Unknown') for m in selected)
            print(f"   Committees: {', '.join(sorted(committees))}")
            print(f"   Date range: {min(m.get('date', '') for m in selected)} to {max(m.get('date', '') for m in selected)}")

        return selected


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Interactive meeting selector for voice enrollment'
    )
    parser.add_argument(
        '--caption-dir',
        default='voice_enrollment/captions',
        help='Directory containing caption files'
    )
    parser.add_argument(
        '--audio-dir',
        default='voice_enrollment/audio',
        help='Directory containing audio files'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Target year for meetings (default: 2025)'
    )
    parser.add_argument(
        '--max-selections',
        type=int,
        default=10,
        help='Maximum number of meetings to select (default: 10)'
    )
    parser.add_argument(
        '--output',
        default='voice_enrollment/database/selected_meetings.json',
        help='Output file for selected meetings'
    )
    parser.add_argument(
        '--auto-select',
        type=int,
        metavar='N',
        help='Auto-select top N meetings without interaction'
    )

    args = parser.parse_args()

    # Create selector
    selector = MeetingSelector(args.caption_dir, args.audio_dir)

    # Run selection
    if args.auto_select:
        # Non-interactive mode
        print(f"\n🤖 Auto-selecting top {args.auto_select} meetings...")
        meetings = selector.scan_and_filter(year=args.year, session_type='session')
        suggestions = selector.suggest_best_meetings(meetings, count=args.auto_select)
        selector.display_suggestions(suggestions)
        selected = suggestions[:args.auto_select]
        print(f"\n✅ Auto-selected {len(selected)} meetings")
    else:
        # Interactive mode
        selected = selector.run_interactive_session(
            year=args.year,
            max_selections=args.max_selections
        )

    # Save selection
    if selected:
        selector.save_selection(selected, args.output)

        print("\n🚀 Next steps:")
        print(f"   1. Review selection in: {args.output}")
        print("   2. Run enrollment script: python voice_enrollment/enroll_voices.py")
    else:
        print("\n⚠️  No meetings selected. Enrollment cannot proceed.")


if __name__ == '__main__':
    main()
