# Voice Enrollment Database

Legislator-centric voice profile database for New Mexico Legislature speaker identification.

## Architecture

Each of the 112 legislators has ONE voice profile built from multiple audio samples across different meetings. This enables:
- Cross-committee identification
- Floor speech identification
- Guest appearance detection

## Directory Structure

```
database/
├── CLAUDE.md                    # This file
├── profile_manager.py           # Core profile management API
├── enrollment_progress.json     # Tracks processing status per meeting
└── legislators/                 # Profile directories (112 total)
    ├── christine_chandler/
    │   └── profile.json         # Voice profile with samples and embeddings
    ├── andrea_romero/
    └── ... (one per legislator)
```

## Profile Schema (v1.0.0)

```json
{
  "schema_version": "1.0.0",
  "legislator": {
    "name": "Full Name",
    "chamber": "House|Senate",
    "district": "number",
    "party": "Democrat|Republican",
    "committees": ["HJC", "HTR", ...],
    "slug": "filesystem_safe_name"
  },
  "voice_samples": [
    {
      "meeting_id": "hjc_012325",
      "speaker_id": "SPEAKER_07",
      "clip_path": "speaker_clips/hjc_012325/SPEAKER_07.wav",
      "segments": 157,
      "total_time": 342.5,
      "meeting_date": "2025-01-23",
      "committee": "HJC",
      "added": "2026-01-31T22:30:00Z"
    }
  ],
  "embeddings": {
    "model": "nemo_titanet|speechbrain_ecapa|null",
    "vector": [192-dim float array],
    "last_updated": "ISO timestamp"
  },
  "stats": {
    "total_samples": 3,
    "total_segments": 523,
    "total_speech_time": 1247.3,
    "meetings_covered": ["hjc_012325", "hafc_012425"],
    "first_enrolled": "ISO timestamp",
    "last_updated": "ISO timestamp"
  }
}
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `profile_manager.py` | Core API: init, get/save profiles, add samples |
| `../label_meeting.py` | Interactive labeling with profile updates |
| `../enroll_batch.py` | Batch processing orchestrator |

## Usage

### Initialize database
```bash
python database/profile_manager.py init
```

### Check enrollment status
```bash
python database/profile_manager.py status
```

### Add voice sample to legislator
```python
from database.profile_manager import ProfileManager

pm = ProfileManager()
pm.add_voice_sample(
    legislator="Christine Chandler",
    meeting_id="hjc_012325",
    speaker_id="SPEAKER_07",
    clip_path="speaker_clips/hjc_012325/SPEAKER_07.wav",
    segments=157,
    total_time=342.5,
    meeting_date="2025-01-23",
    committee="HJC"
)
```

### Get committee roster
```python
members = pm.get_committee_roster("HJC")
```

## Committee Codes

**House Standing (17):** HAAW, HAFC, HCED, HCPA, HED, HEEA, HEEB, HENR, HGEIA, HHHS, HJC, HLVMA, HPS, HRDLC, HTPWCI, HTR, HXRC

**Senate Standing (9):** SCC, SCON, SED, SFC, SHPA, SIRCA, SJC, SRULES, STBT

**Interim (24):** ALC, CBPC, CCJ, CSS, ERDPC, FRS, IAC, IPOC, LEC, LESC, LFC, LGC, LHHS, MFA, MVAC, NMFA, PSCO, RHMC, RSTP, STTC, TSROC, TIRS, WNR, ZFFSS, ZLICW
