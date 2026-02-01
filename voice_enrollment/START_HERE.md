# Voice Enrollment - Getting Started

## Prerequisites Setup (One-Time)

### 1. Get HuggingFace Token

You need a HuggingFace token to download the Pyannote diarization model.

**Steps:**
1. Go to https://huggingface.co/settings/tokens
2. Click "New token" 
3. Name it "pyannote-access" (or whatever you like)
4. Select "Read" access
5. Click "Generate"
6. Copy the token (starts with "hf_...")

### 2. Accept Model Agreement

You must accept the user agreement for the diarization model:

1. Go to https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click "Agree and access repository"
3. Also accept: https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM

### 3. Set Environment Variable

On the server, set your token:

```bash
export HF_TOKEN='hf_your_token_here'
```

To make it permanent, add to ~/.bashrc:
```bash
echo "export HF_TOKEN='hf_your_token_here'" >> ~/.bashrc
source ~/.bashrc
```

---

## Running Voice Enrollment

Once the token is set up, run the enrollment:

```bash
cd ~/Roadrunner_Monitor
./voice_enrollment/setup_and_enroll.sh
```

**What will happen:**

1. **Diarization (10-15 min)** - Detects speakers in the HAFC meeting
   - Identifies 8-20 speakers automatically
   - Shows segments and duration for each speaker

2. **Embedding Generation (3-5 min)** - Creates voice prints
   - Generates 192-dimensional vectors for each speaker
   - Samples 10 voice clips per speaker

3. **Manual Labeling (5-10 min)** - YOU identify who's who
   - System shows you detected speakers
   - System shows HAFC committee roster
   - You match Speaker 0, Speaker 1, etc. to actual legislators
   - You can skip non-members (staff, witnesses)

4. **Database Creation** - Saves voice prints
   - Creates `voice_enrollment/database/voice_database.json`
   - Creates summary report

---

## Interactive Labeling Tips

When the script asks you to identify speakers:

**Watch the meeting video to help identify:**
- Open the meeting video alongside the terminal
- Check timestamps to see who's speaking
- Chair/leader usually has most speaking time (SPEAKER_00)

**Common patterns:**
- SPEAKER_00: Usually the committee chair (Nathan Small for HAFC)
- SPEAKER_01: Often vice chair or most active member
- Short segments: Probably staff or witnesses (skip these)

**Commands during labeling:**
- Enter number (1-18): Assign speaker to that committee member
- Enter "skip": Skip this speaker (not a committee member)
- Enter "done": Finish labeling early

---

## Output Files

After enrollment completes:

```
voice_enrollment/database/
├── voice_database.json         # Main database (192-dim embeddings)
└── voice_database_summary.txt  # Human-readable summary
```

**Next Step:** Build the speaker identifier module to use these voice prints!

---

## Troubleshooting

### "HuggingFace token not found"
- Make sure you exported HF_TOKEN
- Check: `echo $HF_TOKEN`

### "Error loading diarization pipeline"
- Make sure you accepted the model agreement
- Try: `huggingface-cli login` (alternative to HF_TOKEN)

### "Insufficient good segments"
- Normal for some speakers with very short speaking time
- Just skip them and continue

### Diarization is slow
- This is normal - diarization is computationally intensive
- 220MB audio file = ~10-15 minutes processing
- Go get coffee! ☕

---

## Important Notes

⚠️ **This will NOT affect your live workflow**
- All files are in `voice_enrollment/` directory
- No changes to production transcription pipeline
- Your meeting today will process normally

✅ **Safe to run**
- Creates new files only
- Doesn't modify existing code
- Completely isolated from production

---

## Questions?

After enrollment, we'll build the speaker identification module that uses these voice prints to automatically identify speakers in new meetings.

