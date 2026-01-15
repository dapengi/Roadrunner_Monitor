# modules/speaker_id.py

import re
import logging

from data.committee_rosters import get_committee_rosters
from data.committee_mapping import _clean_committee_text
# Removed: from config import SPEAKER_CONFIDENCE_THRESHOLD # No longer needed if not doing advanced matching

logger = logging.getLogger(__name__)


def normalize_name(name):
    """
    Normalize a name for matching (remove quotes, standardize spacing, handle common variations).
    This function is no longer strictly needed for the simplified speaker ID,
    but kept for potential future use or if other parts of the system rely on it.
    """
    name = re.sub(r'["\']', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Generate common variations for matching (e.g., "John Smith" -> "John", "Smith", "John S.")
    parts = name.split()
    variations = {name.lower()}
    if len(parts) > 1:
        variations.add(parts[0].lower()) # First name
        variations.add(parts[-1].lower()) # Last name
        if len(parts) > 1 and parts[0] and parts[-1]:
            variations.add(f"{parts[0][0].lower()}. {parts[-1].lower()}") # J. Smith
            variations.add(f"{parts[0].lower()} {parts[-1].lower()}") # john smith
    return variations


def get_committee_members_for_meeting(meeting_title):
    """
    Get the member list for a specific committee meeting.
    This function is still useful for context, even if not used for speaker assignment right now.
    """
    try:
        if ' - ' in meeting_title:
            committee_name_raw = meeting_title.split(' - ')[-1].strip()
        else:
            committee_name_raw = meeting_title.strip()
        
        cleaned_committee_name = _clean_committee_text(committee_name_raw)
        
        rosters = get_committee_rosters()
        
        for roster_name, members in rosters.items():
            if _clean_committee_text(roster_name) == cleaned_committee_name:
                logger.info(f"Matched committee '{meeting_title}' to roster '{roster_name}' (exact cleaned match)")
                return members
            
            roster_words = set(_clean_committee_text(roster_name).split())
            cleaned_words = set(cleaned_committee_name.split())
            
            common_words = len(roster_words.intersection(cleaned_words))
            
            if common_words >= 2:
                logger.info(f"Matched committee '{meeting_title}' to roster '{roster_name}' (fuzzy match, {common_words} common words)")
                return members
        
        logger.warning(f"No committee roster found for: '{meeting_title}' (cleaned: '{cleaned_committee_name}')")
        return []
        
    except Exception as e:
        logger.error(f"Error getting committee members for '{meeting_title}': {e}")
        return []


def enhance_formatted_transcript_with_names(transcript_text, committee_members):
    """
    Enhance a formatted transcript string by replacing Speaker 0, Speaker 1, etc. 
    with actual committee member names when possible.
    
    Args:
        transcript_text: Formatted transcript string with "Speaker X:" labels
        committee_members: List of committee member names
        
    Returns:
        Enhanced transcript with actual names where possible
    """
    try:
        if not committee_members:
            logger.info("No committee members provided, returning transcript as-is")
            return transcript_text
        
        # Extract unique speakers from transcript
        import re
        speaker_pattern = r'Speaker ([A-Z]):'
        speakers_found = re.findall(speaker_pattern, transcript_text)
        unique_speakers = sorted(set(speakers_found))
        
        logger.info(f"Found {len(unique_speakers)} unique speakers in transcript: {unique_speakers}")
        logger.info(f"Available committee members: {len(committee_members)} members")
        
        if len(unique_speakers) > len(committee_members):
            logger.warning(f"More speakers ({len(unique_speakers)}) than committee members ({len(committee_members)})")
        
        # Create speaker mapping using heuristics
        speaker_mapping = {}
        
        # For now, map speakers to committee members based on order
        # In the future, this could be enhanced with voice analysis or context clues
        for i, speaker_letter in enumerate(unique_speakers):
            if i < len(committee_members):
                # Use first/last name for brevity in transcript
                full_name = committee_members[i]
                if ' ' in full_name:
                    # Use last name for most members, but handle special cases
                    parts = full_name.split()
                    if len(parts) >= 2:
                        display_name = parts[-1]  # Last name
                        speaker_mapping[speaker_letter] = display_name
                    else:
                        speaker_mapping[speaker_letter] = full_name
                else:
                    speaker_mapping[speaker_letter] = full_name
            else:
                # Keep as generic speaker if we run out of committee members
                speaker_mapping[speaker_letter] = f"Speaker {speaker_letter}"
        
        # Apply the mapping to the transcript
        enhanced_transcript = transcript_text
        for speaker_letter, name in speaker_mapping.items():
            old_pattern = f"Speaker {speaker_letter}:"
            new_pattern = f"{name}:"
            enhanced_transcript = enhanced_transcript.replace(old_pattern, new_pattern)
        
        logger.info(f"Enhanced transcript with speaker mappings: {speaker_mapping}")
        return enhanced_transcript
        
    except Exception as e:
        logger.error(f"Error enhancing transcript with names: {e}")
        return transcript_text


def identify_speakers_in_transcript(transcript_data, committee_members):
    """
    Process transcript data with speaker diarization labels.
    Works with both WhisperX format and Sherpa-ONNX formatted string output.
    Maps speaker labels to actual committee member names when possible.
    """
    try:
        # Handle case where transcript_data is a string (formatted transcript from Sherpa-ONNX)
        if isinstance(transcript_data, str):
            logger.info("Processing formatted transcript string for speaker identification")
            return enhance_formatted_transcript_with_names(transcript_data, committee_members)
        
        if not transcript_data or not isinstance(transcript_data, dict):
            logger.warning("Invalid transcript data format")
            return transcript_data
        
        # Check for segments (WhisperX format)
        if 'segments' in transcript_data:
            # Process segments with speaker information
            speaker_mapping = {}
            
            for segment in transcript_data['segments']:
                if 'speaker' in segment and segment['speaker']:
                    original_speaker = segment['speaker']
                    
                    # Convert SPEAKER_XX format to Speaker A, Speaker B, etc.
                    if original_speaker.startswith('SPEAKER_'):
                        if original_speaker not in speaker_mapping:
                            # Create readable speaker label
                            speaker_letter = chr(ord('A') + len(speaker_mapping))
                            speaker_mapping[original_speaker] = f"Speaker {speaker_letter}"
                        
                        segment['speaker'] = speaker_mapping[original_speaker]
                    elif not original_speaker or original_speaker == "Unknown Speaker":
                        segment['speaker'] = "Unknown Speaker"
            
            logger.info(f"Speaker identification completed. Found {len(speaker_mapping)} speakers.")
            return transcript_data
        
        # Check for words (alternative WhisperX format)
        elif 'words' in transcript_data:
            speaker_mapping = {}
            
            for word in transcript_data['words']:
                if 'speaker' in word and word['speaker']:
                    original_speaker = word['speaker']
                    
                    # Convert SPEAKER_XX format to Speaker A, Speaker B, etc.
                    if original_speaker.startswith('SPEAKER_'):
                        if original_speaker not in speaker_mapping:
                            # Create readable speaker label
                            speaker_letter = chr(ord('A') + len(speaker_mapping))
                            speaker_mapping[original_speaker] = f"Speaker {speaker_letter}"
                        
                        word['speaker'] = speaker_mapping[original_speaker]
                    elif not original_speaker or original_speaker == "Unknown Speaker":
                        word['speaker'] = "Unknown Speaker"
            
            logger.info(f"Speaker identification completed. Found {len(speaker_mapping)} speakers.")
            return transcript_data
        
        else:
            logger.warning("No segments or words found in transcript data")
            return transcript_data
        
    except Exception as e:
        logger.error(f"Error in WhisperX speaker identification: {e}")
        return transcript_data


