#!/usr/bin/env python3
"""
Speaker Detection and Segmentation for Legislative Captions
Attempts to identify speaker changes based on timing gaps, linguistic patterns, and other heuristics.
"""

import csv
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import argparse


class SpeakerDetector:
    def __init__(self):
        # Thresholds for detecting speaker changes
        self.long_pause_threshold = 3.0  # seconds
        self.medium_pause_threshold = 1.5  # seconds
        self.short_pause_threshold = 0.8  # seconds
        
        # Linguistic patterns that often indicate speaker changes
        self.speaker_patterns = [
            r'^(thank you|thanks?)\.?\s',
            r'^(good morning|good afternoon|good evening)\.?\s',
            r'^(mr\.|ms\.|mrs\.|madam|senator|representative|chair|chairwoman|chairman)\s',
            r'^(yes|no|well|so|now|ok|okay|alright|all right)\.?\s',
            r'^\w+\s+(here|speaking)\.?\s',
            r'^(my name is|i\'?m)\s',
            r'^(next|moving on|let me)',
            r'^\w+\?\s*$',  # Single word questions
            r'^(uh|um|er)\.?\s',  # Hesitation at start
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.speaker_patterns]
        
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
    
    def has_speaker_pattern(self, text: str) -> bool:
        """Check if text contains patterns that suggest a new speaker"""
        text = text.strip()
        for pattern in self.compiled_patterns:
            if pattern.match(text):
                return True
        return False
    
    def is_likely_speaker_change(self, prev_segment: Dict, curr_segment: Dict, pause_duration: float) -> Tuple[bool, str]:
        """
        Determine if this is likely a speaker change based on multiple factors
        Returns (is_change, reason)
        """
        reasons = []
        
        # Long pause - very likely speaker change
        if pause_duration >= self.long_pause_threshold:
            reasons.append(f"long pause ({pause_duration:.1f}s)")
        
        # Medium pause with linguistic indicators
        elif pause_duration >= self.medium_pause_threshold:
            if self.has_speaker_pattern(curr_segment['Content']):
                reasons.append(f"medium pause ({pause_duration:.1f}s) + speech pattern")
            elif len(curr_segment['Content'].strip()) > 50:  # Substantial content after pause
                reasons.append(f"medium pause ({pause_duration:.1f}s) + substantial content")
        
        # Short pause but strong linguistic indicators
        elif pause_duration >= self.short_pause_threshold:
            if self.has_speaker_pattern(curr_segment['Content']):
                content = curr_segment['Content'].strip()
                # Strong indicators even with short pause
                if any(pattern in content.lower() for pattern in ['thank you', 'my name is', 'good morning', 'good afternoon']):
                    reasons.append(f"short pause ({pause_duration:.1f}s) + strong speech pattern")
        
        # Check for questions followed by answers
        prev_content = prev_segment['Content'].strip()
        curr_content = curr_segment['Content'].strip()
        
        if prev_content.endswith('?') and pause_duration >= self.short_pause_threshold:
            reasons.append(f"question-answer pattern")
        
        # Check for formal introductions
        if re.search(r'(my name is|i\'?m \w+)', curr_content, re.IGNORECASE):
            reasons.append("formal introduction")
        
        # Check for thank you patterns (often indicates end of one speaker, start of another)
        if re.search(r'^(thank you|thanks)', curr_content, re.IGNORECASE):
            reasons.append("thank you transition")
        
        return len(reasons) > 0, "; ".join(reasons)
    
    def detect_speakers(self, captions: List[Dict]) -> List[Dict]:
        """
        Analyze captions and detect likely speaker changes
        Returns list of segments with speaker change indicators
        """
        if not captions:
            return []
        
        segments = []
        current_speaker_id = 1
        
        # First segment always starts a new speaker
        first_segment = {
            'speaker_id': current_speaker_id,
            'start_time': captions[0]['Begin'],
            'segments': [captions[0]],
            'content_preview': captions[0]['Content'][:100] + "..." if len(captions[0]['Content']) > 100 else captions[0]['Content'],
            'confidence': 'high',
            'reason': 'first speaker'
        }
        segments.append(first_segment)
        
        # Analyze subsequent segments
        for i in range(1, len(captions)):
            prev_caption = captions[i-1]
            curr_caption = captions[i]
            
            # Calculate pause duration
            pause_duration = self.calculate_pause_duration(prev_caption['End'], curr_caption['Begin'])
            
            # Check if this is likely a speaker change
            is_change, reason = self.is_likely_speaker_change(prev_caption, curr_caption, pause_duration)
            
            if is_change:
                # Start new speaker segment
                current_speaker_id += 1
                confidence = 'high' if pause_duration >= self.long_pause_threshold else 'medium'
                
                new_segment = {
                    'speaker_id': current_speaker_id,
                    'start_time': curr_caption['Begin'],
                    'segments': [curr_caption],
                    'content_preview': curr_caption['Content'][:100] + "..." if len(curr_caption['Content']) > 100 else curr_caption['Content'],
                    'confidence': confidence,
                    'reason': reason
                }
                segments.append(new_segment)
            else:
                # Add to current speaker segment
                segments[-1]['segments'].append(curr_caption)
        
        # Calculate end times and full content for each segment
        for segment in segments:
            segment['end_time'] = segment['segments'][-1]['End']
            segment['full_content'] = ' '.join([seg['Content'] for seg in segment['segments']])
            segment['duration_seconds'] = len(segment['segments']) * 0.25  # Rough estimate
            segment['word_count'] = len(segment['full_content'].split())
        
        return segments
    
    def export_speaker_segments(self, segments: List[Dict], output_file: str, format_type: str = 'txt'):
        """Export speaker segments in various formats"""
        
        if format_type == 'txt':
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("LEGISLATIVE TRANSCRIPT - SPEAKER SEGMENTS\n")
                f.write("=" * 60 + "\n\n")
                
                for i, segment in enumerate(segments, 1):
                    f.write(f"SPEAKER {segment['speaker_id']} ")
                    f.write(f"(Confidence: {segment['confidence']}) ")
                    f.write(f"[{segment['start_time'][:19]}]\n")
                    f.write(f"Reason: {segment['reason']}\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{segment['full_content']}\n\n")
        
        elif format_type == 'csv':
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Speaker_ID', 'Start_Time', 'End_Time', 'Duration_Seconds', 
                               'Word_Count', 'Confidence', 'Reason', 'Content'])
                
                for segment in segments:
                    writer.writerow([
                        segment['speaker_id'],
                        segment['start_time'],
                        segment['end_time'],
                        len(segment['segments']) * 0.25,  # Rough duration
                        segment['word_count'],
                        segment['confidence'],
                        segment['reason'],
                        segment['full_content']
                    ])
        
        elif format_type == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)
        
        elif format_type == 'vtt':
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                f.write("NOTE\nSpeaker-segmented transcript\n\n")
                
                for segment in segments:
                    start_time = self._convert_timestamp_vtt(segment['start_time'])
                    end_time = self._convert_timestamp_vtt(segment['end_time'])
                    
                    f.write(f"{segment['speaker_id']}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"<v Speaker {segment['speaker_id']}>{segment['full_content']}\n\n")
    
    def _convert_timestamp_vtt(self, iso_timestamp: str) -> str:
        """Convert ISO timestamp to VTT format"""
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S.%f")[:-3]
        except:
            return "00:00:00.000"
    
    def generate_summary_report(self, segments: List[Dict]) -> str:
        """Generate a summary report of speaker detection results"""
        total_segments = len(segments)
        high_confidence = len([s for s in segments if s['confidence'] == 'high'])
        medium_confidence = len([s for s in segments if s['confidence'] == 'medium'])
        
        avg_words_per_segment = sum(s['word_count'] for s in segments) / total_segments if total_segments > 0 else 0
        
        report = f"""
SPEAKER DETECTION SUMMARY REPORT
================================

Total Speaker Segments: {total_segments}
High Confidence: {high_confidence} ({high_confidence/total_segments*100:.1f}%)
Medium Confidence: {medium_confidence} ({medium_confidence/total_segments*100:.1f}%)

Average Words per Segment: {avg_words_per_segment:.1f}

Detection Reasons:
"""
        
        # Count reasons
        reason_counts = {}
        for segment in segments:
            reason = segment['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            report += f"  - {reason}: {count} times\n"
        
        return report


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
    parser = argparse.ArgumentParser(description='Detect speaker changes in legislative captions')
    parser.add_argument('input_file', help='Input CSV file with captions')
    parser.add_argument('--output', '-o', default='speaker_segments', 
                       help='Output filename prefix (default: speaker_segments)')
    parser.add_argument('--formats', nargs='+', 
                       choices=['txt', 'csv', 'json', 'vtt'],
                       default=['txt'],
                       help='Output formats (default: txt)')
    parser.add_argument('--threshold', type=float, default=3.0,
                       help='Minimum pause threshold for speaker changes (default: 3.0 seconds)')
    
    args = parser.parse_args()
    
    print("Loading captions...")
    captions = load_captions_from_csv(args.input_file)
    print(f"Loaded {len(captions)} caption segments")
    
    print("Analyzing speaker patterns...")
    detector = SpeakerDetector()
    detector.long_pause_threshold = args.threshold
    
    segments = detector.detect_speakers(captions)
    
    print(f"\nDetected {len(segments)} potential speakers")
    
    # Generate summary
    summary = detector.generate_summary_report(segments)
    print(summary)
    
    # Export in requested formats
    for fmt in args.formats:
        output_file = f"{args.output}.{fmt}"
        detector.export_speaker_segments(segments, output_file, fmt)
        print(f"Exported speaker segments: {output_file}")
    
    print("\nSpeaker detection complete!")


if __name__ == "__main__":
    main()