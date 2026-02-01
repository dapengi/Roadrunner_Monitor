#!/usr/bin/env python3
import json
import os
import sys

# Add data directory to path
sys.path.insert(0, '/home/josh/roadrunner_granite/data')
from committee_rosters import COMMITTEE_ROSTERS

DIARIZATION_FILE = 'temp/hjc_012325_diarization.json'
CLIPS_DIR = 'speaker_clips/hjc_012325'
OUTPUT_FILE = 'database/hjc_012325_labels.json'

# Load diarization
with open(DIARIZATION_FILE) as f:
    diar_data = json.load(f)

speakers = sorted(set(seg['speaker'] for seg in diar_data['segments']))
print(f'Found {len(speakers)} speakers to label')
print()

# Show roster
roster = COMMITTEE_ROSTERS['HJC']
print('HJC Roster:')
for i, member in enumerate(roster, 1):
    party = 'D' if member['party'] == 'Democrat' else 'R'
    print(f'  {i:2}. {member["name"]:30} (Dist {member["district"]:2}, {party})')
print()
print('Commands:')
print('  - Enter number (1-11) to assign to roster member')
print('  - Enter name directly (e.g., "Christine Chandler")')
print('  - Enter "skip" to skip this speaker')
print('  - Enter "done" to finish')
print()
print('NOTE: Audio clips are on your local machine at:')
print('      /Users/jh/Roadrunner_Monitor_Granite/voice_enrollment/speaker_clips/hjc_012325/')
print('      Open them with: afplay <filename>')
print()

# Labeling
labels = {}
for speaker in speakers:
    # Show info
    segments = [s for s in diar_data['segments'] if s['speaker'] == speaker]
    total_time = sum(s['end'] - s['start'] for s in segments)
    
    print(f'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print(f'{speaker}: {len(segments)} segments, {total_time:.1f}s total')
    print(f'\n  🎵 On your Mac, play: afplay hjc_012325/{speaker}.wav')
    print(f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
    
    # Get label
    while True:
        label = input(f'Label for {speaker} (number/name/skip/done): ').strip()
        
        if label.lower() == 'done':
            print('\nFinishing labeling...')
            break
        elif label.lower() == 'skip':
            print(f'Skipped {speaker}')
            break
        elif label.isdigit():
            idx = int(label) - 1
            if 0 <= idx < len(roster):
                labels[speaker] = roster[idx]['name']
                print(f'✓ {speaker} → {labels[speaker]}')
                break
            else:
                print(f'Invalid number. Choose 1-{len(roster)}')
        elif label:
            # Direct name entry
            labels[speaker] = label
            print(f'✓ {speaker} → {label}')
            break
        else:
            print('Please enter a number, name, skip, or done')
    
    if label.lower() == 'done':
        break

# Save
os.makedirs('database', exist_ok=True)
output_data = {
    'meeting': 'HJC 01/23/25',
    'diarization_file': DIARIZATION_FILE,
    'labels': labels
}

with open(OUTPUT_FILE, 'w') as f:
    json.dump(output_data, f, indent=2)

print(f'\n✅ Labels saved to {OUTPUT_FILE}')
print(f'Labeled {len(labels)} of {len(speakers)} speakers')
