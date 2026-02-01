# Voice Enrollment from Diarization - Quick Start

## Overview

This approach uses Pyannote diarization to automatically detect speakers in meeting recordings, then you manually label who each speaker is to build the voice database.

**Advantages:**
- Works with existing long meeting recordings
- No need to find/extract individual clips
- Automatic speaker detection
- One meeting can enroll 10-20 legislators

**Process:**
1. Run diarization on meeting audio → detects speakers (Speaker 0, Speaker 1, etc.)
2. Generate voice embeddings for each speaker
3. Manual labeling → you identify which speaker is which person
4. Save voice database

---

## Prerequisites

Install Pyannote diarization model (one-time setup):

```bash
cd ~/Roadrunner_Monitor
source venv/bin/activate

# Install pyannote-audio if not already installed
pip install pyannote-audio

# Accept user agreement (required for diarization model)
# Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
# Click "Agree and access repository"
```

You'll also need a Hugging Face token:
1. Go to https://huggingface.co/settings/tokens
2. Create a new token (read access is sufficient)
3. Set environment variable:
```bash
export HF_TOKEN="your_token_here"
```

---

## Usage

### Step 1: Pick a Meeting

Choose one of your existing meeting audio files:
```bash
ls -lh voice_enrollment/audio/
```

Example files you have:
- `House_Appropriation_012425.mp3` (HAFC, Jan 24)
- `House_Judiciary_012325.mp3` (HJC, Jan 23)
- `House - Rural Development, Land Grants And Cultural Affairs.mp3` (HRDLC)

### Step 2: Run Enrollment

```bash
cd ~/Roadrunner_Monitor
source venv/bin/activate

# Example with HAFC meeting
python3 voice_enrollment/enroll_from_diarization.py \
    voice_enrollment/audio/House_Appropriation_012425.mp3 \
    --committee HAFC

# Example with HJC meeting
python3 voice_enrollment/enroll_from_diarization.py \
    voice_enrollment/audio/House_Judiciary_012325.mp3 \
    --committee HJC
```

### Step 3: Watch the Process

**Stage 1: Diarization (5-15 minutes)**
```
🎙️  Running diarization on: House_Appropriation_012425.mp3
   This may take several minutes...
   ✓ Detected 15 speakers
   - SPEAKER_00: 45 segments, 180.5s total
   - SPEAKER_01: 32 segments, 142.3s total
   - SPEAKER_02: 28 segments, 98.7s total
   ...
```

**Stage 2: Generate Embeddings (2-5 minutes)**
```
🔊 Generating embeddings for 15 speakers...
   Processing SPEAKER_00...
      ✓ Generated embedding from 10 samples
   Processing SPEAKER_01...
      ✓ Generated embedding from 10 samples
   ...
```

**Stage 3: Manual Labeling (Interactive)**
```
🏷️  SPEAKER LABELING INTERFACE
================================================================================

Committee: HAFC
Members in roster: 18
Detected speakers: 15

📊 DETECTED SPEAKERS:
SPEAKER_00: 10 samples, 45 segments, 180.5s total
SPEAKER_01: 10 samples, 32 segments, 142.3s total
...

👥 COMMITTEE ROSTER:
 1. Nathan P. Small (Democrat, District 36)
 2. Meredith A. Dixon (Democrat, District 20)
 3. Jack Chatfield (Republican, District 67)
 4. Brian G. Baca (Republican, District 8)
...

LABELING INSTRUCTIONS:
For each detected speaker, enter the member number from the roster above.
Enter 'skip' to skip a speaker (not a committee member).
Enter 'done' when finished labeling.

🎤 SPEAKER_00
   Samples: 10, Duration: 180.5s
   Who is SPEAKER_00? (1-18, 'skip', 'done'): 1

   ✓ Labeled as: Nathan P. Small

🎤 SPEAKER_01
   Samples: 10, Duration: 142.3s
   Who is SPEAKER_01? (1-18, 'skip', 'done'): 2

   ✓ Labeled as: Meredith A. Dixon

🎤 SPEAKER_02
   Samples: 10, Duration: 98.7s
   Who is SPEAKER_02? (1-18, 'skip', 'done'): skip

   ⊘ Skipping SPEAKER_02

...
```

### Step 4: Review Output

After labeling, the voice database is saved:

```
✅ ENROLLMENT COMPLETE
================================================================================

📂 Database: voice_enrollment/database/voice_database.json
```

Check the summary:
```bash
cat voice_enrollment/database/voice_database_summary.txt
```

---

## Tips for Labeling

**How to identify speakers:**

1. **Listen to the audio** around the timestamps where a speaker talks
2. **Check the meeting video** - match timestamps to see who's speaking
3. **Look for patterns:**
   - Chair/leader usually speaks most (SPEAKER_00)
   - Vice chair next most
   - Frequent speakers are likely committee members
   - Short/rare speakers may be staff or witnesses (skip these)

**Strategies:**

- **Start with the obvious:** Chair and frequent speakers first
- **Skip unknowns:** Use 'skip' for staff, witnesses, or unclear speakers
- **You can stop early:** Type 'done' when you've labeled enough members
- **Aim for 8-12 members:** That's enough for a good proof-of-concept

**Watch the meeting video:**
```bash
# Example timestamps to check
# SPEAKER_00 talks at: 0:03:15, 0:12:30, 0:45:22
# Open video at those times to see who it is
```

---

## Command Options

```bash
python3 voice_enrollment/enroll_from_diarization.py \
    <audio_file> \
    --committee <HAFC|HJC|HRDLC> \
    [--output voice_database.json] \
    [--min-speakers 5] \
    [--max-speakers 30] \
    [--samples-per-speaker 10]
```

**Options:**
- `--committee`: Required - which committee (HAFC, HJC, or HRDLC)
- `--output`: Where to save voice database (default: `voice_enrollment/database/voice_database.json`)
- `--min-speakers`: Minimum expected speakers (default: 5)
- `--max-speakers`: Maximum expected speakers (default: 30)
- `--samples-per-speaker`: Voice samples to collect per speaker (default: 10)

---

## Troubleshooting

### Problem: Diarization is very slow

**Solution:** Use a shorter meeting or subset of audio:
```bash
# Extract first 30 minutes of meeting
ffmpeg -i meeting.mp3 -t 1800 -c copy meeting_30min.mp3

# Run enrollment on shorter file
python3 voice_enrollment/enroll_from_diarization.py meeting_30min.mp3 --committee HAFC
```

### Problem: Too many speakers detected

**Solution:** Increase min-speakers to reduce over-segmentation:
```bash
python3 voice_enrollment/enroll_from_diarization.py meeting.mp3 \
    --committee HAFC \
    --min-speakers 10 \
    --max-speakers 20
```

### Problem: HuggingFace authentication error

**Solution:** Set your HF token:
```bash
export HF_TOKEN="hf_xxxxxxxxxxxxx"
# Or install huggingface-cli and login
huggingface-cli login
```

### Problem: Can't tell who a speaker is

**Solution:**
- Use 'skip' - it's okay to not label everyone
- Focus on committee members who speak frequently
- Staff and witnesses can be skipped

---

## Next Steps

After enrollment:

1. **Test identification** on a new meeting (not used for enrollment)
2. **Measure accuracy** by comparing automated IDs to actual speakers
3. **Expand database** by processing more meetings
4. **Integrate into pipeline** once accuracy is satisfactory

---

## Example Session

```bash
cd ~/Roadrunner_Monitor
source venv/bin/activate

# Run enrollment on HAFC meeting
python3 voice_enrollment/enroll_from_diarization.py \
    voice_enrollment/audio/House_Appropriation_012425.mp3 \
    --committee HAFC

# Wait for diarization... (~10 min)
# Wait for embeddings... (~3 min)
# Label speakers... (~5-10 min)

# Check results
cat voice_enrollment/database/voice_database_summary.txt

# Done! Voice database ready for testing
```
