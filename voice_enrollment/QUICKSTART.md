# Voice Enrollment Quick Start Guide

## Phase 1: Proof-of-Concept (5-10 Meetings from 2025)

### Prerequisites

1. **Download 5-10 session meetings from 2025:**
   - Choose major committees: HAFC, SFC, SJC, HJC
   - Get both caption files (VTT/SRT/TXT) and audio files (MP4/WAV/MP3)
   - Use consistent naming: `YYYYMMDD-{TYPE}-{COMMITTEE}-{START}-{END}.{ext}`
   - Example: `20250115-HOUSE-HAFC-900AM-1200PM.vtt` and `20250115-HOUSE-HAFC-900AM-1200PM.mp4`

2. **Place files in directories:**
   ```bash
   # Caption files
   cp /path/to/captions/*.{vtt,srt,txt} voice_enrollment/captions/

   # Audio files
   cp /path/to/audio/*.{mp4,wav,mp3} voice_enrollment/audio/
   ```

### Step-by-Step Process

#### 1. Validate Setup

Check if everything is ready:

```bash
cd ~/Roadrunner_Monitor
python3 voice_enrollment/validate_setup.py
```

**Expected output:**
```
✅ PASS - Directories
✅ PASS - Dependencies
✅ PASS - Pyannote Model
✅ PASS - Committee Rosters
✅ PASS - Files
✅ PASS - Scripts

✅ ALL CHECKS PASSED - System ready for enrollment!
```

If any checks fail, follow the fix instructions provided.

---

#### 2. Select Meetings

Run the interactive meeting selector:

```bash
python3 voice_enrollment/meeting_selector.py
```

**Example session:**
```
🔍 Scanning directories for 2025 session meetings...
   Found 8 total meetings
   Filtered to 8 2025 session meetings

📋 SUGGESTED MEETINGS FOR VOICE ENROLLMENT
================================================================================

1. [85/100] 2025-01-15 - HOUSE - HAFC
   Time: 900AM to 1200PM (3h)
   ⭐ Full Attendance | 🏛️ Major Committee | ✨ High Quality

2. [85/100] 2025-01-20 - SENATE - SFC
   Time: 130PM to 430PM (3h)
   ⭐ Full Attendance | 🏛️ Major Committee | ✨ High Quality

...

📝 SELECT MEETINGS FOR ENROLLMENT (Max: 10)
Options:
  - Enter numbers (e.g., '1,3,5' or '1-5')
  - Enter 'all' to select all suggested meetings
  - Enter 'top5' or 'top10' to select top N

Your selection: top5

✓ Selected top 5 meetings

✅ Selection saved to: voice_enrollment/database/selected_meetings.json
```

**Quick options:**
- Type `all` to select all meetings
- Type `top5` to select top 5
- Type `1-5` to select meetings 1 through 5
- Type `1,3,5` to select specific meetings

**Or auto-select without interaction:**
```bash
python3 voice_enrollment/meeting_selector.py --auto-select 5
```

---

#### 3. Run Enrollment

Process selected meetings and build voice database:

```bash
python3 voice_enrollment/enroll_voices.py
```

**Expected output:**
```
🎙️  VOICE ENROLLMENT - STARTING
================================================================================

📂 Loaded 5 selected meetings from voice_enrollment/database/selected_meetings.json

⚙️  Processing: 2025-01-15-HAFC
   Parsed 234 caption segments
   Found 12 unique speakers
   Processing speaker: Senator Figueroa (18 segments)
      ✓ Generated 10 embeddings
   Processing speaker: Representative Martinez (15 segments)
      ✓ Generated 9 embeddings
   ...

🔨 Building voice database...
   ✓ Matched: Senator Figueroa -> Senator Figueroa (0.95)
   ✓ Matched: Representative Martinez -> Representative Martinez (0.92)
   ...

✅ Database created with 35 legislators

💾 Voice database saved to: voice_enrollment/database/voice_database.json
📄 Summary saved to: voice_enrollment/database/voice_database_summary.txt
📊 Enrollment report saved to: voice_enrollment/database/enrollment_report.txt

✅ VOICE ENROLLMENT - COMPLETED
================================================================================

📂 Database: voice_enrollment/database/voice_database.json
📊 Report: voice_enrollment/database/enrollment_report.txt

🎯 Next step: Test speaker identification on new meetings
```

**Processing time:**
- ~5-10 minutes per meeting
- Depends on duration and number of speakers
- Progress displayed in real-time

---

#### 4. Review Results

Check the generated files:

**Voice Database** (`voice_database.json`)
```bash
cat voice_enrollment/database/voice_database.json
```

This contains the 192-dimensional voice embeddings for each enrolled legislator.

**Human-Readable Summary** (`voice_database_summary.txt`)
```bash
cat voice_enrollment/database/voice_database_summary.txt
```

Example output:
```
VOICE DATABASE ENROLLMENT SUMMARY
================================================================================

Created: 2025-01-11T10:30:00
Model: pyannote/wespeaker-voxceleb-resnet34-LM
Legislators enrolled: 35

ENROLLED LEGISLATORS:
--------------------------------------------------------------------------------

Senator Figueroa
  Chamber: Senate | District: 1 | Party: Democrat
  Samples: 10 from 2 meetings
  Confidence: 0.95
  Meetings:
    - 2025-01-15 HAFC (6 samples)
    - 2025-01-20 SFC (4 samples)

Representative Martinez
  Chamber: House | District: 23 | Party: Republican
  Samples: 9 from 3 meetings
  Confidence: 0.92
  Meetings:
    - 2025-01-15 HAFC (3 samples)
    - 2025-01-22 HAFC (4 samples)
    - 2025-01-25 HJC (2 samples)
...
```

**Enrollment Report** (`enrollment_report.txt`)
```bash
cat voice_enrollment/database/enrollment_report.txt
```

Shows statistics and any errors encountered during processing.

---

### Troubleshooting

#### Problem: No meetings found

Check if files are in the correct directories:
```bash
ls -lh voice_enrollment/captions/
ls -lh voice_enrollment/audio/
```

Ensure filenames match (except extension):
- ✅ `20250115-HOUSE-HAFC-900AM-1200PM.vtt` + `20250115-HOUSE-HAFC-900AM-1200PM.mp4`
- ❌ `meeting1.vtt` + `meeting2.mp4`

#### Problem: Pyannote model not found

The model will auto-download on first use. If it fails:
```bash
python3 -c "from pyannote.audio import Inference; Inference('pyannote/wespeaker-voxceleb-resnet34-LM')"
```

This will manually trigger the download.

#### Problem: Speaker not matched

Check the enrollment report for unmatched speakers. Common causes:
- Speaker name format doesn't match roster (normalize manually)
- Legislator not on committee roster for that meeting
- Low similarity score (< 0.70)

Solution: Review `voice_enrollment/database/enrollment_report.txt` for details.

---

### Next Steps After Phase 1

Once enrollment is complete:

1. **Test on New Meeting:**
   - Run transcription on a 2025 meeting NOT used in enrollment
   - Compare automated speaker IDs to actual speakers
   - Measure accuracy

2. **Expand Coverage:**
   - Add more meetings to increase legislator sample sizes
   - Include different committees for broader coverage
   - Focus on legislators with low sample counts

3. **Tune Thresholds:**
   - Adjust confidence threshold (default: 0.85)
   - Balance precision vs. recall based on use case

4. **Production Integration:**
   - Connect to main transcription pipeline
   - Add automated speaker identification step
   - Generate reports with speaker names instead of A/B/C labels

---

### File Locations

```
voice_enrollment/
├── captions/                           # Input: Your caption files
├── audio/                              # Input: Your audio files
├── database/
│   ├── selected_meetings.json          # Output: Selected meetings list
│   ├── voice_database.json             # Output: Main voice database
│   ├── voice_database_summary.txt      # Output: Human-readable summary
│   └── enrollment_report.txt           # Output: Statistics and errors
├── reports/                            # Future: Additional reports
└── temp/                               # Temporary: Auto-cleaned

```

---

### Command Reference

```bash
# Validate setup
python3 voice_enrollment/validate_setup.py

# Select meetings (interactive)
python3 voice_enrollment/meeting_selector.py

# Select meetings (auto-select top 5)
python3 voice_enrollment/meeting_selector.py --auto-select 5

# Run enrollment
python3 voice_enrollment/enroll_voices.py

# View results
cat voice_enrollment/database/voice_database_summary.txt
cat voice_enrollment/database/enrollment_report.txt
```

---

### Questions?

See the full README at `voice_enrollment/README.md` for detailed documentation.
