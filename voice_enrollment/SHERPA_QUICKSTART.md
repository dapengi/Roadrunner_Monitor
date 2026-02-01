# Voice Enrollment - Sherpa-ONNX Approach

## Quick Start

Run enrollment with Sherpa (no compatibility issues!):

```bash
cd ~/Roadrunner_Monitor
./voice_enrollment/run_sherpa_enrollment.sh
```

## What This Does

**Hybrid Approach - Best of Both Worlds:**
- Sherpa-ONNX: Speaker diarization (already working on your system!)
- Pyannote: Voice embeddings (the part that loaded successfully)

**Timeline:**
- Diarization: 5-10 min (Sherpa analyzing audio)
- Embeddings: 2-3 min (Pyannote voice prints)
- Your labeling: 5-10 min (match speakers to legislators)

## Labeling Tips

Speakers shown sorted by speaking time:
- **Most talking** → Usually committee chair (Nathan Small for HAFC)
- **Active speakers** → Committee members  
- **Short segments** → Staff or witnesses (skip with 'skip')

## Why This Works

✅ Uses your existing Sherpa setup
✅ No torchaudio compatibility hell
✅ No HuggingFace authentication hassles
✅ Pyannote embeddings (industry standard for voice ID)
✅ Completely isolated from live workflow

## Output

Creates:
- `database/voice_database.json` - Voice prints database
- `database/voice_database_summary.txt` - Human-readable summary
