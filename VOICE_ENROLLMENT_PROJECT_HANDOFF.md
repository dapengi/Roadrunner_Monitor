# Voice Enrollment Project - Handoff Documentation

**Date:** January 31, 2026
**Status:** Infrastructure Complete - Ready for Implementation
**Next Phase:** Voice Enrollment System Development

---

## Project Overview

Building a voice identification system for New Mexico Legislature that can:
- Identify legislators speaking in committee meetings
- Identify legislators on the floor
- Identify legislators speaking in committees they're not members of
- Use shared voice profiles across all contexts (not committee-specific)

### Key Design Decision
**Legislator-centric architecture** instead of meeting-centric:
- Each legislator has ONE voice profile used everywhere
- Voice profiles built from multiple audio samples across different meetings
- System matches against all 112 legislators, uses committee rosters as priors
- Eliminates redundant labeling and enables cross-committee identification

---

## Current Status

### ✅ Completed

1. **Master Legislator Roster**
   - **112 total legislators** (70 House + 42 Senate)
   - **50 total committees** (17 House + 9 Senate + 24 Interim)
   - **817 total committee assignments**
   - Built from official CSV data with verified mappings
   - Files: `master_legislator_roster.json`, `master_legislator_roster.py`
   - Location: `/home/josh/roadrunner_granite/data/` (server) and local

2. **Committee Structure**
   - All standing committees mapped with official acronyms
   - All interim committees mapped with official acronyms
   - Complete committee membership for each legislator
   - See `LEGISLATOR_ROSTER_VERIFICATION.txt` for full details

3. **Audio Data Preparation**
   - User is downloading **44 audio files** (2 per committee)
   - Old audio files cleared from server
   - Audio directory ready: `/home/josh/roadrunner_granite/voice_enrollment/audio/`

4. **Existing Diarization Infrastructure**
   - Pyannote 3.1 diarization working on server
   - Can process 3-hour meetings in ~70 minutes
   - Environment: `venv_pyannote` on server
   - Script: `run_diarization_only.py`
   - Clip extraction: `extract_clips_from_json.py` (fixed to accept output directory)

### 🔄 In Progress

- User downloading 44 audio files (2 per committee × 22 committees)
- Audio files will be uploaded to server when ready

---

## System Architecture

### Data Structure

```
voice_database/
├── legislators/
│   ├── christine_chandler/
│   │   ├── profile.json          # Name, chamber, district, party, committees
│   │   ├── embeddings.npy        # Voice embedding vector(s)
│   │   └── samples.json          # Audio samples used to build profile
│   ├── andrea_romero/
│   └── ... (112 total)
```

### Voice Enrollment Workflow

**Phase 1: Enrollment (Building Profiles)**
```
1. Run diarization on committee meeting → detect speakers
2. Extract audio clips for each speaker
3. User labels speakers by matching to legislator roster
4. Add labeled clips to legislator profiles (not meeting files!)
5. Build/update voice embeddings from accumulated samples
6. One legislator = one profile, built from all their appearances
```

**Phase 2: Identification (Using Profiles)**
```
1. Run diarization on any meeting (committee/floor)
2. Extract speaker embeddings
3. Compare against ALL 112 legislator profiles
4. Use committee roster as Bayesian prior (increase confidence for members)
5. Output: SPEAKER_07 → Christine Chandler (94% confidence)
```

### Key Benefits
- ✅ Each legislator labeled once, identified everywhere
- ✅ Works for floor speeches (no roster restriction)
- ✅ Works when legislators visit other committees
- ✅ More robust (multiple samples improve accuracy)
- ✅ Efficient (no redundant labeling)

---

## Technical Details

### Server Information
- **Host:** `josh@10.0.0.173`
- **Base directory:** `/home/josh/roadrunner_granite/`
- **Python environment:** `/home/josh/roadrunner_granite/venv_pyannote/`
- **Audio storage:** `/home/josh/roadrunner_granite/voice_enrollment/audio/`
- **Voice database:** `/home/josh/roadrunner_granite/voice_enrollment/database/` (to be created)

### Required Environment Variables
- `HF_TOKEN` - HuggingFace token for Pyannote models
- Located in: `/home/josh/roadrunner_granite/.env`

### Dependencies
- **Pyannote Audio 3.1** - Speaker diarization
- **NeMo TitaNet** - Voice embeddings (mentioned in earlier work)
- **librosa** - Audio processing
- **soundfile** - WAV file handling

### Committee Acronyms Reference

**House Standing (17):**
- HAAW, HAFC, HCED, HCPA, HED, HEEA, HEEB, HENR, HGEIA, HHHS, HJC, HLVMA, HPS, HRDLC, HTPWCI, HTR, HXRC

**Senate Standing (9):**
- SCC, SCON, SED, SFC, SHPA, SIRCA, SJC, SRULES, STBT

**Interim (24):**
- ALC, CBPC, CCJ, CSS, ERDPC, FRS, IAC, IPOC, LEC, LESC, LFC, LGC, LHHS, MFA, MVAC, NMFA, PSCO, RHMC, RSTP, STTC, TSROC, TIRS, WNR, ZFFSS, ZLICW

(Note: Some interim committees have Z prefix - ZFFSS, ZLICW)

---

## Files and Locations

### Master Roster Files
- **JSON:** `data/master_legislator_roster.json` (machine-readable)
- **Python:** `data/master_legislator_roster.py` (importable module)
- **Report:** `data/LEGISLATOR_ROSTER_VERIFICATION.txt` (human-readable verification)

### Voice Enrollment Files (Server)
- **Diarization script:** `run_diarization_only.py`
- **Clip extraction:** `voice_enrollment/extract_clips_from_json.py`
- **Old labeling scripts:** `voice_enrollment/label_hjc.py` (meeting-specific, needs redesign)
- **Audio directory:** `voice_enrollment/audio/` (currently empty, awaiting uploads)
- **Clips directory:** `voice_enrollment/speaker_clips/`
- **Temp directory:** `voice_enrollment/temp/` (diarization outputs)
- **Database directory:** `voice_enrollment/database/` (to be created)

### Previous Work Examples
- **HAFC diarization:** `voice_enrollment/temp/hafc_012325_diarization.json` (25 speakers, 4223 segments)
- **HJC diarization:** `voice_enrollment/temp/hjc_012325_diarization.json` (15 speakers, 2000 segments)
- **HAFC clips:** User labeled 14 legislators from HAFC meeting

---

## Implementation Plan

### Phase 1: Build Voice Enrollment Infrastructure (DO THIS FIRST)

**1.1 Design Database Schema**
```python
# legislator profile structure
{
    "name": "Christine Chandler",
    "chamber": "House",
    "district": "43",
    "party": "Democrat",
    "committees": ["HJC", "HTR", "HXRC", "CCJ", "ALC", "LEC", "RSTP", "LHHS", "STTC"],
    "voice_samples": [
        {
            "source": "hjc_012325",
            "speaker_id": "SPEAKER_07",
            "clip_path": "voice_enrollment/speaker_clips/hjc_012325/SPEAKER_07.wav",
            "segments": 157,
            "total_time": 342.5,
            "date": "2025-01-23"
        }
    ],
    "embeddings": {
        "model": "nemo_titanet",
        "vector": [...],  # 192-dimension vector
        "last_updated": "2025-01-23"
    },
    "stats": {
        "total_samples": 3,
        "total_segments": 523,
        "total_time": 1247.3,
        "meetings_covered": ["hjc_012325", "hafc_012425", "floor_012625"]
    }
}
```

**1.2 Create Database Directory Structure**
```bash
mkdir -p /home/josh/roadrunner_granite/voice_enrollment/database/legislators
```

**1.3 Update Labeling Workflow**
- Modify labeling scripts to ADD samples to legislator profiles
- Not create meeting-specific label files
- Allow progressive profile building across multiple meetings

**1.4 Create Enrollment Tools**
- Script to extract clips from diarization
- Interactive labeling interface (download clips locally for ease)
- Profile builder that computes/updates embeddings
- Profile viewer/validator

### Phase 2: Enroll Legislators from 44 Audio Files

**Strategy:**
- Process committee meetings systematically
- As you encounter legislators, add samples to their profiles
- Each legislator gets labeled once, contributes samples from all appearances
- Track coverage: which legislators have strong profiles vs weak

**Workflow per meeting:**
```bash
1. Upload audio to server: voice_enrollment/audio/committee_name_date.mp3
2. Run diarization: python run_diarization_only.py audio/file.mp3 temp/output.json
3. Extract clips: python extract_clips_from_json.py temp/output.json audio/file.mp3 speaker_clips/meeting_id
4. Download clips locally for labeling
5. Run labeling interface (labels speakers → legislator names)
6. Update legislator profiles with new samples
7. Recompute embeddings for updated profiles
```

**Priority Order:**
- Start with committees with many members (HAFC, LFC, etc.) - more coverage
- Aim for 2-3 samples per legislator minimum
- Track which legislators still need samples

### Phase 3: Build Identification System

**3.1 Embedding Generator**
- Compute embeddings for each speaker in diarized meeting
- Use same model as enrollment (NeMo TitaNet for consistency)

**3.2 Matcher**
- Compare speaker embeddings against all 112 legislator profiles
- Cosine similarity or distance metric
- Apply committee roster as Bayesian prior (boost scores for members)
- Threshold for confidence (e.g., 80% to assign name)

**3.3 Output Format**
```json
{
    "meeting": "hjc_012325",
    "identifications": [
        {
            "speaker_id": "SPEAKER_07",
            "legislator": "Christine Chandler",
            "confidence": 0.94,
            "match_score": 0.87,
            "roster_boost": 0.07
        }
    ]
}
```

### Phase 4: Integration & Testing

**4.1 Test Cases**
- Committee meetings (should identify all/most members)
- Floor speeches (no roster, harder test)
- Guest appearances (legislators in committees they're not on)

**4.2 Integration**
- Add to existing transcript pipeline
- Replace SPEAKER_XX labels with legislator names
- Update webhook output format

---

## Known Issues & Considerations

### Technical Challenges
1. **Name variations** - Nicknames handled in roster (e.g., "Elizabeth \"Liz\" Stefanics")
2. **Audio quality** - Some meetings may have poor audio
3. **Overlapping speech** - Diarization struggles with crosstalk
4. **Similar voices** - May need higher thresholds for similar-sounding legislators
5. **Minimum samples** - Need enough data per legislator for robust profile

### Workflow Considerations
1. **Labeling time** - 44 files × 15-25 speakers each = significant manual work
2. **Coverage gaps** - Not all legislators may appear in available audio
3. **Profile updates** - Strategy for adding new samples to existing profiles
4. **Confidence thresholds** - Balance between false positives and unlabeled speakers

### Design Decisions to Make
1. **Embedding model choice** - Confirm NeMo TitaNet vs alternatives
2. **Similarity metric** - Cosine similarity vs Euclidean distance vs other
3. **Profile update strategy** - Average embeddings vs retrain vs other
4. **Minimum sample requirements** - How many clips needed for reliable profile?
5. **Confidence thresholds** - What score is "confident enough" to assign name?

---

## Quick Reference Commands

### Server Access
```bash
ssh josh@10.0.0.173
cd /home/josh/roadrunner_granite
```

### Run Diarization
```bash
export HF_TOKEN={{YOUR_HUGGINGFACE_TOKEN}}
/home/josh/roadrunner_granite/venv_pyannote/bin/python run_diarization_only.py \
  voice_enrollment/audio/meeting.mp3 \
  voice_enrollment/temp/meeting_diarization.json
```

### Extract Clips
```bash
/home/josh/roadrunner_granite/venv_pyannote/bin/python \
  voice_enrollment/extract_clips_from_json.py \
  voice_enrollment/temp/meeting_diarization.json \
  voice_enrollment/audio/meeting.mp3 \
  voice_enrollment/speaker_clips/meeting_id
```

### Download Clips Locally (for labeling)
```bash
scp -r josh@10.0.0.173:/home/josh/roadrunner_granite/voice_enrollment/speaker_clips/meeting_id \
  /Users/jh/Roadrunner_Monitor_Granite/voice_enrollment/speaker_clips/
```

### Load Master Roster
```python
import sys
sys.path.insert(0, '/home/josh/roadrunner_granite/data')
from master_legislator_roster import LEGISLATORS

# Get legislator info
legislator = LEGISLATORS['Christine Chandler']
print(f"{legislator['name']} - {legislator['chamber']} District {legislator['district']}")
print(f"Committees: {', '.join(legislator['committees'])}")
```

---

## Next Steps for Implementation

### Immediate (This Weekend Goal)
1. **Design voice database schema** - Finalize legislator profile structure
2. **Create database infrastructure** - Directories, initial profile files
3. **Update labeling workflow** - New scripts that build profiles, not meeting labels
4. **Process first batch of audio** - Start enrolling legislators

### Short Term (Next Week)
1. **Build enrollment coverage tracker** - Know which legislators need more samples
2. **Create profile validator** - Check profile quality, sample diversity
3. **Begin systematic enrollment** - Work through all 44 audio files

### Medium Term
1. **Implement identification system** - Embedding comparison, matching logic
2. **Test on held-out meetings** - Validate accuracy
3. **Integrate with transcript pipeline** - Replace speaker labels with names

---

## Resources & Documentation

### Key Files to Read First
1. `/home/josh/roadrunner_granite/data/LEGISLATOR_ROSTER_VERIFICATION.txt` - All legislators and committees
2. `/home/josh/roadrunner_granite/data/master_legislator_roster.py` - Roster data structure
3. `/home/josh/roadrunner_granite/run_diarization_only.py` - Diarization implementation
4. `/home/josh/roadrunner_granite/voice_enrollment/extract_clips_from_json.py` - Clip extraction

### Previous Conversation Context
- User wants system completed "by end of weekend"
- 44 audio files incoming (2 per committee)
- User emphasized: legislators speak across committees and on floor - need universal identification
- User prefers audio clips on local machine for easier labeling (download via scp)

### Important Notes
- Production server: `josh@100.120.112.67` (separate from this dev server)
- Main transcript pipeline runs on production, outputs to n8n webhooks
- This voice system will eventually integrate with production pipeline
- Git repo exists but hasn't been updated with recent changes

---

## Questions to Resolve

Before proceeding, consider:

1. **Embedding model confirmed?** - NeMo TitaNet mentioned earlier, verify this is what you want
2. **Profile update strategy?** - When adding new samples, recompute embedding or average?
3. **Minimum viable profile?** - How many samples needed before profile is "usable"?
4. **Labeling interface preference?** - CLI, web interface, or other?
5. **Floor speech handling?** - Different strategy since no roster available?
6. **Unknown speaker handling?** - What to do with speakers who don't match any profile?
7. **Confidence output?** - Always output confidence scores or only when below threshold?

---

## Success Criteria

System is successful when:
- ✅ Can identify 112 legislators from voice alone
- ✅ Works in committee meetings, floor speeches, and guest appearances
- ✅ Achieves >80% accuracy on test meetings
- ✅ Provides confidence scores for all identifications
- ✅ Integrated with existing transcript pipeline
- ✅ Replaces SPEAKER_XX labels with legislator names in final output

---

**Project started:** January 2026
**Infrastructure completed:** January 31, 2026
**Ready for:** Voice enrollment implementation
**Expected completion:** This weekend (user's goal)

Good luck with the implementation! The hard design work is done - now it's execution time. 🚀
