# Voice Enrollment System - Phase 1

## Overview

This system creates a voice biometrics database for identifying New Mexico legislators by their voices. It uses Pyannote.audio to generate voice embeddings from meeting recordings and matches speakers to committee members.

**Target Accuracy:** 95%
**Phase 1 Scope:** 5-10 session meetings from 2025 (proof-of-concept)

---

## Directory Structure

```
voice_enrollment/
├── captions/           # Place downloaded caption files here (VTT/SRT/TXT)
├── audio/              # Place downloaded audio files here (MP4/WAV/MP3)
├── database/           # Generated voice database and reports
├── reports/            # Enrollment reports and statistics
├── temp/               # Temporary audio segments (auto-cleaned)
├── caption_parser.py   # Parses VTT/SRT/TXT caption formats
├── meeting_scanner.py  # Scans directories and builds meeting inventory
├── voice_embedder.py   # Generates Pyannote voice embeddings
├── meeting_selector.py # Interactive meeting selection tool
├── enroll_voices.py    # Main enrollment script
└── README.md           # This file
```

---

## Phase 1 Workflow

### Step 1: Prepare Meeting Files

Download 5-10 session meetings from 2025 and place files in appropriate directories:

**Caption Files** → `voice_enrollment/captions/`
- Supported formats: VTT, SRT, TXT
- Must contain speaker labels (e.g., "SENATOR FIGUEROA:", "Rep. Martinez:")
- Filename format: `YYYYMMDD-{TYPE}-{COMMITTEE}-{START}-{END}.{ext}`
- Example: `20250115-HOUSE-HAFC-900AM-1200PM.vtt`

**Audio Files** → `voice_enrollment/audio/`
- Supported formats: MP4, WAV, MP3
- Must match caption file basename
- Example: `20250115-HOUSE-HAFC-900AM-1200PM.mp4`

**Tips for file selection:**
- ✅ Prefer session meetings (full attendance)
- ✅ Choose major committees: HAFC, SFC, SJC, HJC
- ✅ Longer meetings = more voice samples
- ✅ Good audio quality (clear voices, minimal background noise)

### Step 2: Select Meetings

Run the interactive meeting selector:

```bash
cd ~/Roadrunner_Monitor
python3 voice_enrollment/meeting_selector.py
```

**Interactive Mode:**
The tool will:
1. Scan `captions/` and `audio/` directories
2. Auto-filter for 2025 session meetings
3. Score meetings by quality (session type, committee, duration)
4. Display top suggestions with quality indicators
5. Let you select which meetings to use

**Selection Options:**
```
Enter 'all'      - Select all suggested meetings
Enter 'top5'     - Select top 5 meetings
Enter '1,3,5'    - Select specific meetings
Enter '1-5'      - Select range of meetings
Enter 'done'     - Finish selection
```

**Auto-Select Mode:**
```bash
# Auto-select top 10 meetings without interaction
python3 voice_enrollment/meeting_selector.py --auto-select 10
```

**Output:** `voice_enrollment/database/selected_meetings.json`

### Step 3: Run Enrollment

Process selected meetings and build voice database:

```bash
python3 voice_enrollment/enroll_voices.py
```

**What happens:**
1. Loads selected meetings from `selected_meetings.json`
2. Parses caption files to extract speaker segments
3. Extracts audio segments for each speaker
4. Generates Pyannote embeddings (192-dim vectors)
5. Matches speakers to legislators using committee rosters
6. Averages embeddings across meetings for robust profiles
7. Saves voice database as JSON

**Expected Runtime:**
- ~5-10 minutes per meeting
- Depends on meeting duration and number of speakers
- Progress displayed in real-time

### Step 4: Review Results

Check generated files in `voice_enrollment/database/`:

**`voice_database.json`** - Main voice database
```json
{
  "version": "1.0",
  "created": "2025-01-11T10:30:00",
  "model": "pyannote/wespeaker-voxceleb-resnet34-LM",
  "embedding_dim": 192,
  "legislators": {
    "senator_figueroa": {
      "name": "Senator Figueroa",
      "chamber": "Senate",
      "district": "1",
      "party": "Democrat",
      "embedding": [0.123, 0.456, ...],  // 192 dimensions
      "enrollment": {
        "sample_count": 15,
        "meeting_count": 3,
        "match_confidence": 0.92
      }
    }
  }
}
```

**`voice_database_summary.txt`** - Human-readable summary
- Lists all enrolled legislators
- Shows sample counts and meeting sources
- Displays match confidence scores

**`enrollment_report.txt`** - Detailed statistics
- Total meetings processed
- Segments processed and embeddings generated
- Errors and warnings

---

## Quality Indicators

### Meeting Quality Scores

The system assigns quality scores (0-100) based on:

| Factor | Points |
|--------|--------|
| Session meeting (vs. interim) | +30 |
| Major committee (HAFC/SFC/SJC/HJC) | +20 |
| Has both caption and audio files | +50 |

**Quality tiers:**
- 🌟 80-100: Excellent (full attendance, major committee)
- ✅ 60-79: Good (session meeting or major committee)
- ⚠️ 40-59: Fair (interim or minor committee)
- ❌ 0-39: Poor (missing files or data)

### Match Confidence Scores

Speaker-to-legislator matching uses fuzzy name matching:

| Score | Meaning |
|-------|---------|
| 0.90-1.00 | Excellent match (last name + title match) |
| 0.80-0.89 | Good match (strong similarity) |
| 0.70-0.79 | Fair match (acceptable threshold) |
| < 0.70 | Rejected (too uncertain) |

**Matching algorithm:**
1. Normalize speaker names (Sen. → Senator, Rep. → Representative)
2. Calculate string similarity (SequenceMatcher)
3. Boost score if last names match exactly (+0.3)
4. Filter committee roster to likely attendees
5. Return best match above 0.70 threshold

---

## File Naming Convention

**Format:** `YYYYMMDD-{TYPE}-{COMMITTEE}-{STARTTIME}-{ENDTIME}`

**Examples:**
- `20250115-HOUSE-HAFC-900AM-1200PM.vtt` - House HAFC session
- `20250120-SENATE-SFC-130PM-430PM.mp4` - Senate SFC session
- `20251105-IC-LFC-830AM-1130AM.txt` - LFC interim committee

**Components:**
- `YYYYMMDD` - Meeting date (ISO format)
- `TYPE` - `HOUSE`, `SENATE`, or `IC` (interim committee)
- `COMMITTEE` - Acronym (HAFC, SFC, LFC, etc.)
- `STARTTIME` - Start time (e.g., 900AM, 130PM)
- `ENDTIME` - End time (e.g., 1200PM, 430PM)

**Supported Extensions:**
- Captions: `.vtt`, `.srt`, `.txt`
- Audio: `.mp4`, `.wav`, `.mp3`

---

## Caption File Formats

### WebVTT (.vtt)

```
WEBVTT

00:05:23.000 --> 00:05:45.000
SENATOR FIGUEROA: Thank you, Mr. Chair. I'd like to discuss the budget proposal...

00:05:45.000 --> 00:06:12.000
REPRESENTATIVE MARTINEZ: I agree with the Senator's point about funding...
```

### SubRip (.srt)

```
1
00:05:23,000 --> 00:05:45,000
SENATOR FIGUEROA: Thank you, Mr. Chair. I'd like to discuss the budget proposal...

2
00:05:45,000 --> 00:06:12,000
REPRESENTATIVE MARTINEZ: I agree with the Senator's point about funding...
```

### Plain Text (.txt)

```
[00:05:23] SENATOR FIGUEROA: Thank you, Mr. Chair. I'd like to discuss...
[00:05:45] REPRESENTATIVE MARTINEZ: I agree with the Senator's point...
```

**Required elements:**
- ✅ Timestamps (any reasonable format)
- ✅ Speaker labels (SENATOR X:, Rep. Y:, etc.)
- ✅ Transcribed speech text

---

## Troubleshooting

### Problem: No meetings found

**Cause:** Caption or audio files not in correct directories

**Solution:**
1. Check file locations:
   ```bash
   ls voice_enrollment/captions/
   ls voice_enrollment/audio/
   ```
2. Ensure filenames match exactly (except extension)
3. Verify filename format matches convention

### Problem: Speaker not matched to legislator

**Cause:** Name variation or legislator not on committee roster

**Solution:**
1. Check speaker name in caption file (normalize manually if needed)
2. Verify legislator is on committee roster in `data/committee_rosters.py`
3. Check match confidence in enrollment report
4. If needed, add name variation to matching algorithm

### Problem: Low sample count for legislator

**Cause:** Speaker didn't talk much in selected meetings

**Solution:**
1. Select more meetings from different dates
2. Ensure audio quality is good (clear voice, minimal noise)
3. Check caption file has accurate speaker labels
4. Verify audio segments are > 2 seconds (minimum length)

### Problem: Enrollment script fails

**Cause:** Missing dependencies or Pyannote model not loaded

**Solution:**
1. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```
2. Check Pyannote model is downloaded:
   ```bash
   python3 -c "from pyannote.audio import Inference; Inference('pyannote/wespeaker-voxceleb-resnet34-LM')"
   ```
3. Check error details in `enrollment_report.txt`

---

## Command-Line Options

### Meeting Selector

```bash
python3 voice_enrollment/meeting_selector.py [OPTIONS]

Options:
  --caption-dir DIR      Caption files directory (default: voice_enrollment/captions)
  --audio-dir DIR        Audio files directory (default: voice_enrollment/audio)
  --year YEAR            Target year (default: 2025)
  --max-selections N     Maximum meetings to select (default: 10)
  --output FILE          Output JSON file (default: voice_enrollment/database/selected_meetings.json)
  --auto-select N        Auto-select top N meetings without interaction
```

### Voice Enrollment

```bash
python3 voice_enrollment/enroll_voices.py [OPTIONS]

Options:
  --selection-file FILE  Selected meetings JSON (default: voice_enrollment/database/selected_meetings.json)
  --output-dir DIR       Output directory (default: voice_enrollment/database)
  --temp-dir DIR         Temporary directory (default: voice_enrollment/temp)
```

---

## Next Steps (Post-Phase 1)

After successful Phase 1 enrollment:

1. **Test Identification:** Run speaker ID on a new meeting not in training set
2. **Measure Accuracy:** Compare automated IDs to ground truth labels
3. **Expand Database:** Add more meetings to improve coverage
4. **Production Integration:** Connect to main transcription pipeline
5. **Confidence Thresholds:** Tune thresholds for production use

---

## Technical Details

### Voice Embeddings

- **Model:** `pyannote/wespeaker-voxceleb-resnet34-LM`
- **Dimensions:** 192 (floating point)
- **Normalization:** L2 normalized for cosine similarity
- **Distance Metric:** Cosine similarity (higher = more similar)
- **Aggregation:** Averaged across multiple samples per speaker

### Speaker Identification Algorithm

1. Extract audio segment from meeting
2. Generate 192-dim embedding using Pyannote
3. Compare to all embeddings in database (cosine similarity)
4. Filter by committee roster (reduce search space)
5. Return best match above confidence threshold (default: 0.85)
6. Flag low-confidence matches for manual review

### Performance Optimization

- **Committee filtering:** Reduces search from 154 legislators to ~20-30
- **Embedding caching:** Pre-computed embeddings for O(1) lookup
- **Batch processing:** Multiple segments processed together
- **Early termination:** Stop at high-confidence match (>0.95)

---

## Support

For issues or questions:
1. Check `voice_enrollment/database/enrollment_report.txt` for errors
2. Review this README for troubleshooting steps
3. Contact system administrator

---

**Version:** 1.0
**Last Updated:** 2025-01-11
**Status:** Phase 1 (Proof-of-Concept)
