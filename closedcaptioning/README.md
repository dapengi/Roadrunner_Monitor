# Legislative Caption Downloader

A Python script to download closed captions from New Mexico Legislature Harmony/Sliq.net streaming system.

## Requirements

- Python 3.6+
- `requests` library

```bash
pip install requests
```

## Usage

### Speaker Detection Mode (Recommended)

**Automatically detects speaker changes for improved readability:**

```bash
python caption_downloader_with_speakers.py
```

This enhanced version:
- Identifies when different speakers are talking
- Creates readable transcripts with speaker segments
- Provides speaker transition analysis
- Offers both traditional captions and speaker-segmented transcripts

### Interactive Mode

**Simple prompts for basic caption download:**

```bash
python caption_downloader_interactive.py
```

**Or simply double-click:**
```bash
python run_caption_downloader.py
```

The interactive version will prompt you for:
1. Video URL
2. Output formats (with descriptions)
3. Output directory
4. Confirmation before download

### Command Line Usage

```bash
python caption_downloader.py [URL] --formats [FORMAT1] [FORMAT2] --output-dir [DIRECTORY]
```

### Examples

Download as text file (default):
```bash
python caption_downloader.py "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250819/-1/77483"
```

Download in multiple formats:
```bash
python caption_downloader.py "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250819/-1/77483" --formats txt vtt srt csv json
```

Specify output directory:
```bash
python caption_downloader.py "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250819/-1/77483" --formats txt vtt --output-dir ./downloads
```

### Supported Formats

**Traditional Caption Formats:**
- **txt**: Plain text transcript
- **vtt**: WebVTT format (for web video players)
- **srt**: SubRip format (for video editing software)
- **csv**: CSV with timestamps and content
- **json**: Raw JSON data with full metadata

**Speaker-Enhanced Formats:**
- **speakers.txt**: Readable transcript with speaker segments and timestamps
- **speaker_data.csv**: Speaker analysis data with confidence levels
- **speaker_summary.txt**: Summary of detected speakers and statistics

### Output Files

Files are automatically named based on the video title and metadata:
- Format: `[Title]_[Date]_[ID].[extension]`
- Example: `IC_-_Water_and_Natural_Resources_20250819_77483.txt`

## Features

### Caption Extraction
- Extracts pre-generated captions from archived legislative videos
- Handles timestamp conversion (ISO format to VTT/SRT)
- Multiple output formats for different use cases
- Automatic filename generation based on video metadata
- Error handling and fallback caption extraction methods

### Speaker Detection (NEW!)
- **Automatic speaker change detection** using timing gaps and linguistic patterns
- **Speaker identification** from formal introductions ("My name is...")
- **Confidence scoring** for speaker transitions (high/medium)
- **Readable transcript format** with clear speaker segments
- **Speaker statistics** showing detected speakers and word counts
- **Intelligent merging** of short segments to reduce over-segmentation

### Detection Methods
The speaker detection algorithm uses multiple indicators:
- **Timing analysis**: Long pauses (5+ seconds) indicate likely speaker changes
- **Linguistic patterns**: "Thank you", "Good afternoon", formal introductions
- **Question-answer patterns**: Detecting Q&A transitions
- **Speech patterns**: Recognition of typical speaking transitions
- **Content analysis**: Identifying formal vs. informal speech segments

## How It Works

The script:
1. Fetches the HTML page containing embedded caption data
2. Extracts JSON caption objects from JavaScript variables
3. Converts timestamps to appropriate formats
4. Saves captions in requested formats

## Notes

- Only works with archived videos (not live streams)
- Captions are pre-generated, not real-time
- Currently supports English captions only
- Requires internet connection to fetch video pages

## Testing

Run the test script to verify functionality:
```bash
python test_downloader.py
```