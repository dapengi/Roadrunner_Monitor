#!/usr/bin/env python3
"""
Enhanced Speaker Detection for Legislative Captions
Improved algorithm that combines segments and provides better speaker identification.
"""

import csv
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple
import argparse


class EnhancedSpeakerDetector:
    def __init__(self):
        # More conservative thresholds
        self.major_pause_threshold = 8.0  # Major speaker changes
        self.moderate_pause_threshold = 4.0  # Likely speaker changes
        self.minor_pause_threshold = 2.0  # Possible speaker changes
        
        # Strong indicators of new speakers
        self.strong_speaker_patterns = [
            r'^(thank you.*?)\.\s+(good morning|good afternoon|good evening|my name)',
            r'^(good morning|good afternoon|good evening).*?(madam chair|chair|committee)',
            r'^my name is \w+',
            r'^(thank you.*?)\.\s+(next|moving on|now)',
            r'(thank you.*?)\.\s*$',  # Thank you ending
        ]
        
        # Moderate indicators
        self.moderate_speaker_patterns = [
            r'^(uh|um|well|so|now|ok|okay|alright|all right).*?my name',
            r'^(yes|no),?\s+(madam|mr\.|ms\.|mrs\.)',
            r'question.*?\?$',
            r'^(thank you|thanks?)\.?\s',
        ]
        
        # Compile patterns
        self.strong_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.strong_speaker_patterns]
        self.moderate_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.moderate_speaker_patterns]
        
    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO timestamp string to datetime object"""
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    def calculate_pause_duration(self, prev_end: str, curr_start: str) -> float:
        """Calculate pause duration between caption segments in seconds"""
        try:
            prev_dt = self.parse_timestamp(prev_end)
            curr_dt = self.parse_timestamp(curr_start)
            return (curr_dt - prev_dt).total_seconds()
        except:
            return 0.0
    
    def extract_speaker_name(self, text: str) -> str:
        """Try to extract speaker name from introduction"""
        # Look for "My name is X" patterns
        name_patterns = [
            r'my name\'?s? (\w+(?:\s+\w+){0,2})',
            r'i\'?m (\w+(?:\s+\w+){0,2})',
            r'this is (\w+(?:\s+\w+){0,2})',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Filter out common words that aren't names
                if name.lower() not in ['the', 'a', 'an', 'here', 'going', 'gonna', 'speaking']:
                    return name.title()
        
        return None
    
    def has_strong_speaker_pattern(self, text: str) -> Tuple[bool, str]:
        """Check for strong speaker change indicators"""
        for pattern in self.strong_patterns:
            if pattern.search(text):
                return True, "strong speech pattern"
        return False, ""
    
    def has_moderate_speaker_pattern(self, text: str) -> Tuple[bool, str]:
        """Check for moderate speaker change indicators"""
        for pattern in self.moderate_patterns:
            if pattern.search(text):
                return True, "moderate speech pattern"
        return False, ""
    
    def is_speaker_change(self, prev_segment: Dict, curr_segment: Dict, pause_duration: float) -> Tuple[bool, str, str]:
        """
        Determine if this is a speaker change
        Returns (is_change, confidence, reason)
        """
        curr_text = curr_segment['Content'].strip()
        
        # Major pause - very likely new speaker
        if pause_duration >= self.major_pause_threshold:
            return True, "high", f"major pause ({pause_duration:.1f}s)"
        
        # Strong patterns with any meaningful pause
        has_strong, strong_reason = self.has_strong_speaker_pattern(curr_text)
        if has_strong and pause_duration >= 1.0:
            return True, "high", f"pause ({pause_duration:.1f}s) + {strong_reason}"
        
        # Moderate pause with moderate patterns
        if pause_duration >= self.moderate_pause_threshold:
            has_moderate, moderate_reason = self.has_moderate_speaker_pattern(curr_text)
            if has_moderate:
                return True, "medium", f"moderate pause ({pause_duration:.1f}s) + {moderate_reason}"
            else:
                return True, "medium", f"moderate pause ({pause_duration:.1f}s)"
        
        # Strong patterns even with short pause
        if has_strong:
            return True, "high", strong_reason
        
        # Minor pause with specific patterns
        if pause_duration >= self.minor_pause_threshold:
            # Look for formal greetings
            if re.search(r'^(good morning|good afternoon|good evening)', curr_text, re.IGNORECASE):
                return True, "medium", f"minor pause ({pause_duration:.1f}s) + formal greeting"
            
            # Look for thank you transitions
            if re.search(r'^(thank you|thanks)', curr_text, re.IGNORECASE):
                return True, "medium", f"minor pause ({pause_duration:.1f}s) + thank you transition"
        
        return False, "", ""
    
    def merge_short_segments(self, segments: List[Dict], min_words: int = 10) -> List[Dict]:
        """Merge very short segments with adjacent ones"""
        if not segments:
            return segments
        
        merged = [segments[0]]
        
        for current in segments[1:]:
            prev_segment = merged[-1]
            
            # If current segment is very short, merge with previous
            if current['word_count'] < min_words:
                # Merge content
                prev_segment['segments'].extend(current['segments'])
                prev_segment['end_time'] = current['end_time']
                prev_segment['full_content'] += " " + current['full_content']
                prev_segment['word_count'] += current['word_count']
                
                # Update confidence if current was higher
                if current['confidence'] == 'high' and prev_segment['confidence'] != 'high':
                    prev_segment['confidence'] = 'medium'
            else:
                merged.append(current)
        
        return merged
    
    def detect_speakers(self, captions: List[Dict]) -> List[Dict]:
        """Main speaker detection algorithm"""
        if not captions:
            return []
        
        segments = []
        speaker_count = 1
        
        # First segment
        first_content = captions[0]['Content']
        first_name = self.extract_speaker_name(first_content)
        
        first_segment = {
            'speaker_id': speaker_count,
            'speaker_name': first_name or f"Speaker {speaker_count}",
            'start_time': captions[0]['Begin'],
            'segments': [captions[0]],
            'confidence': 'high',
            'reason': 'session start'
        }
        segments.append(first_segment)
        
        # Process remaining captions
        for i in range(1, len(captions)):
            prev_caption = captions[i-1]
            curr_caption = captions[i]
            
            pause_duration = self.calculate_pause_duration(prev_caption['End'], curr_caption['Begin'])
            is_change, confidence, reason = self.is_speaker_change(prev_caption, curr_caption, pause_duration)
            
            if is_change:
                speaker_count += 1
                speaker_name = self.extract_speaker_name(curr_caption['Content'])
                
                new_segment = {
                    'speaker_id': speaker_count,
                    'speaker_name': speaker_name or f"Speaker {speaker_count}",
                    'start_time': curr_caption['Begin'],
                    'segments': [curr_caption],
                    'confidence': confidence,
                    'reason': reason
                }
                segments.append(new_segment)
            else:
                # Add to current segment
                segments[-1]['segments'].append(curr_caption)
        
        # Calculate derived fields
        for segment in segments:
            segment['end_time'] = segment['segments'][-1]['End']
            segment['full_content'] = ' '.join([s['Content'] for s in segment['segments']])
            segment['word_count'] = len(segment['full_content'].split())
            
            # Create content preview
            if len(segment['full_content']) > 150:
                segment['content_preview'] = segment['full_content'][:147] + "..."
            else:
                segment['content_preview'] = segment['full_content']
        
        # Merge very short segments
        segments = self.merge_short_segments(segments, min_words=8)
        
        return segments
    
    def export_readable_transcript(self, segments: List[Dict], output_file: str):
        """Export a clean, readable transcript"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("NEW MEXICO LEGISLATURE TRANSCRIPT\n")
            f.write("=" * 50 + "\n\n")
            
            for segment in segments:
                # Header with speaker info
                speaker_name = segment['speaker_name']
                start_time = segment['start_time'][11:19]  # Extract HH:MM:SS
                
                f.write(f"{speaker_name.upper()} [{start_time}]\n")
                if segment['confidence'] == 'high':
                    f.write("────────────────────────────────────────\n")
                else:
                    f.write("- - - - - - - - - - - - - - - - - - - - -\n")
                
                # Clean up content
                content = segment['full_content']
                # Fix common transcription issues
                content = re.sub(r'\s+', ' ', content)  # Multiple spaces
                content = re.sub(r'([.!?])\s*([a-z])', r'\1 \2', content)  # Space after punctuation
                
                f.write(f"{content}\n\n")
    
    def export_speaker_csv(self, segments: List[Dict], output_file: str):
        """Export speaker data as CSV"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Speaker_Name', 'Start_Time', 'End_Time', 'Word_Count', 
                           'Confidence', 'Reason', 'Content_Preview'])
            
            for segment in segments:
                writer.writerow([
                    segment['speaker_name'],
                    segment['start_time'],
                    segment['end_time'],
                    segment['word_count'],
                    segment['confidence'],
                    segment['reason'],
                    segment['content_preview']
                ])
    
    def generate_summary(self, segments: List[Dict]) -> str:
        """Generate summary report"""
        total_speakers = len(segments)
        high_conf = len([s for s in segments if s['confidence'] == 'high'])
        
        identified_speakers = len([s for s in segments if not s['speaker_name'].startswith('Speaker ')])
        
        avg_words = sum(s['word_count'] for s in segments) / total_speakers if total_speakers > 0 else 0
        
        summary = f"""
ENHANCED SPEAKER DETECTION SUMMARY
=================================

Total Speaker Segments: {total_speakers}
High Confidence: {high_conf} ({high_conf/total_speakers*100:.1f}%)
Named Speakers Identified: {identified_speakers}
Average Words per Speaker: {avg_words:.1f}

SPEAKERS IDENTIFIED:
"""
        
        for segment in segments:
            if not segment['speaker_name'].startswith('Speaker '):
                start_time = segment['start_time'][11:19]
                summary += f"  - {segment['speaker_name']} [{start_time}] ({segment['word_count']} words)\n"
        
        return summary


def load_captions_from_csv(csv_file: str) -> List[Dict]:
    """Load captions from CSV file"""
    captions = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            captions.append({
                'Begin': row['Start Time'],
                'End': row['End Time'],
                'Content': row['Content']
            })
    return captions


def main():
    parser = argparse.ArgumentParser(description='Enhanced speaker detection for legislative captions')
    parser.add_argument('input_file', help='Input CSV file with captions')
    parser.add_argument('--output', '-o', default='enhanced_transcript', 
                       help='Output filename prefix (default: enhanced_transcript)')
    
    args = parser.parse_args()
    
    print("Loading captions...")
    captions = load_captions_from_csv(args.input_file)
    print(f"Loaded {len(captions)} caption segments")
    
    print("Analyzing speakers with enhanced detection...")
    detector = EnhancedSpeakerDetector()
    segments = detector.detect_speakers(captions)
    
    print(f"Detected {len(segments)} speaker segments")
    
    # Generate summary
    summary = detector.generate_summary(segments)
    print(summary)
    
    # Export files
    detector.export_readable_transcript(segments, f"{args.output}.txt")
    detector.export_speaker_csv(segments, f"{args.output}.csv")
    
    print(f"\nFiles created:")
    print(f"  - {args.output}.txt (readable transcript)")
    print(f"  - {args.output}.csv (speaker data)")
    
    print("\nEnhanced speaker detection complete!")


if __name__ == "__main__":
    main()