#!/usr/bin/env python3
"""
Voice Profile Manager for New Mexico Legislature Voice Identification System.

Manages legislator voice profiles with a legislator-centric architecture where:
- Each legislator has ONE voice profile used for all identification
- Profiles are built from multiple audio samples across different meetings
- System matches against all 112 legislators, uses committee rosters as priors
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np


# Schema version for future migrations
SCHEMA_VERSION = "1.0.0"

# Default paths
DEFAULT_DATABASE_DIR = "/home/josh/roadrunner_granite/voice_enrollment/database"
DEFAULT_LEGISLATORS_DIR = f"{DEFAULT_DATABASE_DIR}/legislators"
MASTER_ROSTER_PATH = "/home/josh/roadrunner_granite/data/master_legislator_roster.json"


def slugify(name: str) -> str:
    """Convert legislator name to filesystem-safe slug.
    
    Examples:
        'Christine Chandler' -> 'christine_chandler'
        'William A. Hall II' -> 'william_a_hall_ii'
        'Elizabeth "Liz" Stefanics' -> 'elizabeth_liz_stefanics'
    """
    # Remove quotes and special chars, convert to lowercase
    slug = name.lower()
    slug = re.sub(r'["\']', '', slug)  # Remove quotes
    slug = re.sub(r'[^a-z0-9\s]', ' ', slug)  # Keep only alphanumeric and spaces
    slug = re.sub(r'\s+', '_', slug.strip())  # Replace spaces with underscores
    return slug


def create_empty_profile(legislator_data: Dict) -> Dict:
    """Create an empty voice profile for a legislator.
    
    Args:
        legislator_data: Dict with name, chamber, district, party, committees
        
    Returns:
        Empty profile dict ready for voice samples
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "legislator": {
            "name": legislator_data["name"],
            "chamber": legislator_data["chamber"],
            "district": legislator_data["district"],
            "party": legislator_data["party"],
            "committees": legislator_data["committees"],
            "slug": slugify(legislator_data["name"])
        },
        "voice_samples": [],
        "embeddings": {
            "model": None,
            "vector": None,
            "last_updated": None
        },
        "stats": {
            "total_samples": 0,
            "total_segments": 0,
            "total_speech_time": 0.0,
            "meetings_covered": [],
            "first_enrolled": None,
            "last_updated": None
        },
        "metadata": {
            "created": datetime.now().isoformat(),
            "notes": []
        }
    }


def create_voice_sample(
    meeting_id: str,
    speaker_id: str,
    clip_path: str,
    segments: int,
    total_time: float,
    meeting_date: str,
    committee: Optional[str] = None
) -> Dict:
    """Create a voice sample record to add to a profile.
    
    Args:
        meeting_id: Identifier for the meeting (e.g., 'hjc_012325')
        speaker_id: Original diarization speaker ID (e.g., 'SPEAKER_07')
        clip_path: Path to the audio clip file
        segments: Number of speech segments in this sample
        total_time: Total speech time in seconds
        meeting_date: Date of the meeting (YYYY-MM-DD)
        committee: Optional committee code (e.g., 'HJC')
        
    Returns:
        Voice sample dict
    """
    return {
        "meeting_id": meeting_id,
        "speaker_id": speaker_id,
        "clip_path": clip_path,
        "segments": segments,
        "total_time": total_time,
        "meeting_date": meeting_date,
        "committee": committee,
        "added": datetime.now().isoformat()
    }


class ProfileManager:
    """Manages legislator voice profiles."""
    
    def __init__(
        self,
        database_dir: str = DEFAULT_DATABASE_DIR,
        roster_path: str = MASTER_ROSTER_PATH
    ):
        """Initialize the profile manager.
        
        Args:
            database_dir: Root directory for the voice database
            roster_path: Path to master legislator roster JSON
        """
        self.database_dir = Path(database_dir)
        self.legislators_dir = self.database_dir / "legislators"
        self.roster_path = Path(roster_path)
        
        # Load master roster
        self.roster = self._load_roster()
        
        # Build name -> slug mapping for lookups
        self._name_to_slug = {
            name: slugify(name) for name in self.roster.keys()
        }
        self._slug_to_name = {v: k for k, v in self._name_to_slug.items()}
        
    def _load_roster(self) -> Dict:
        """Load master legislator roster."""
        with open(self.roster_path, 'r') as f:
            return json.load(f)
    
    def initialize_database(self) -> Dict[str, int]:
        """Initialize the database with empty profiles for all legislators.
        
        Creates directory structure and empty profile.json for each legislator.
        
        Returns:
            Dict with counts of created, skipped, and total profiles
        """
        self.legislators_dir.mkdir(parents=True, exist_ok=True)
        
        created = 0
        skipped = 0
        
        for name, data in self.roster.items():
            slug = slugify(name)
            profile_dir = self.legislators_dir / slug
            profile_path = profile_dir / "profile.json"
            
            if profile_path.exists():
                skipped += 1
                continue
                
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile = create_empty_profile(data)
            
            with open(profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            created += 1
        
        return {
            "created": created,
            "skipped": skipped,
            "total": len(self.roster)
        }
    
    def get_profile(self, identifier: str) -> Optional[Dict]:
        """Get a legislator's profile.
        
        Args:
            identifier: Legislator name or slug
            
        Returns:
            Profile dict or None if not found
        """
        slug = self._resolve_slug(identifier)
        if not slug:
            return None
            
        profile_path = self.legislators_dir / slug / "profile.json"
        
        if not profile_path.exists():
            return None
            
        with open(profile_path, 'r') as f:
            return json.load(f)
    
    def save_profile(self, profile: Dict) -> bool:
        """Save a legislator's profile.
        
        Args:
            profile: Profile dict with legislator.slug field
            
        Returns:
            True if saved successfully
        """
        slug = profile["legislator"]["slug"]
        profile_path = self.legislators_dir / slug / "profile.json"
        
        # Update last modified timestamp
        profile["stats"]["last_updated"] = datetime.now().isoformat()
        
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
            
        return True
    
    def add_voice_sample(
        self,
        legislator: str,
        meeting_id: str,
        speaker_id: str,
        clip_path: str,
        segments: int,
        total_time: float,
        meeting_date: str,
        committee: Optional[str] = None
    ) -> bool:
        """Add a voice sample to a legislator's profile.
        
        Args:
            legislator: Legislator name or slug
            meeting_id: Meeting identifier
            speaker_id: Original diarization speaker ID
            clip_path: Path to the audio clip
            segments: Number of speech segments
            total_time: Total speech time in seconds
            meeting_date: Meeting date (YYYY-MM-DD)
            committee: Optional committee code
            
        Returns:
            True if sample added successfully
        """
        profile = self.get_profile(legislator)
        if not profile:
            return False
        
        # Create sample record
        sample = create_voice_sample(
            meeting_id=meeting_id,
            speaker_id=speaker_id,
            clip_path=clip_path,
            segments=segments,
            total_time=total_time,
            meeting_date=meeting_date,
            committee=committee
        )
        
        # Check for duplicate (same meeting + speaker)
        for existing in profile["voice_samples"]:
            if existing["meeting_id"] == meeting_id and existing["speaker_id"] == speaker_id:
                return False  # Already exists
        
        # Add sample
        profile["voice_samples"].append(sample)
        
        # Update stats
        profile["stats"]["total_samples"] += 1
        profile["stats"]["total_segments"] += segments
        profile["stats"]["total_speech_time"] += total_time
        
        if meeting_id not in profile["stats"]["meetings_covered"]:
            profile["stats"]["meetings_covered"].append(meeting_id)
        
        if not profile["stats"]["first_enrolled"]:
            profile["stats"]["first_enrolled"] = datetime.now().isoformat()
        
        # Invalidate embeddings (need recomputation)
        profile["embeddings"]["vector"] = None
        profile["embeddings"]["last_updated"] = None
        
        return self.save_profile(profile)
    
    def get_enrollment_status(self) -> Dict[str, Any]:
        """Get enrollment status for all legislators.
        
        Returns:
            Dict with enrollment statistics and lists
        """
        enrolled = []
        not_enrolled = []
        weak_profiles = []  # < 3 samples
        
        for name in self.roster.keys():
            profile = self.get_profile(name)
            
            if not profile:
                not_enrolled.append(name)
                continue
                
            sample_count = profile["stats"]["total_samples"]
            
            if sample_count == 0:
                not_enrolled.append(name)
            elif sample_count < 3:
                weak_profiles.append({
                    "name": name,
                    "samples": sample_count,
                    "time": profile["stats"]["total_speech_time"]
                })
                enrolled.append(name)
            else:
                enrolled.append(name)
        
        return {
            "total_legislators": len(self.roster),
            "enrolled": len(enrolled),
            "not_enrolled": len(not_enrolled),
            "weak_profiles": len(weak_profiles),
            "enrolled_names": enrolled,
            "not_enrolled_names": not_enrolled,
            "weak_profile_details": weak_profiles
        }
    
    def get_committee_roster(self, committee_code: str) -> List[str]:
        """Get list of legislators on a committee.
        
        Args:
            committee_code: Committee acronym (e.g., 'HJC', 'HAFC')
            
        Returns:
            List of legislator names
        """
        members = []
        for name, data in self.roster.items():
            if committee_code in data["committees"]:
                members.append(name)
        return sorted(members)
    
    def search_legislators(self, query: str) -> List[str]:
        """Search legislators by partial name match.
        
        Args:
            query: Search string (case-insensitive)
            
        Returns:
            List of matching legislator names
        """
        query_lower = query.lower()
        matches = []
        
        for name in self.roster.keys():
            if query_lower in name.lower():
                matches.append(name)
                
        return sorted(matches)
    
    def _resolve_slug(self, identifier: str) -> Optional[str]:
        """Resolve a name or slug to a slug.
        
        Args:
            identifier: Legislator name or slug
            
        Returns:
            Slug or None if not found
        """
        # Check if it's already a valid slug
        if identifier in self._slug_to_name:
            return identifier
            
        # Check if it's a name
        if identifier in self._name_to_slug:
            return self._name_to_slug[identifier]
            
        return None
    
    def list_all_legislators(self) -> List[Dict]:
        """List all legislators with basic info.
        
        Returns:
            List of dicts with name, chamber, district, party
        """
        legislators = []
        for name, data in self.roster.items():
            profile = self.get_profile(name)
            sample_count = profile["stats"]["total_samples"] if profile else 0
            
            legislators.append({
                "name": name,
                "chamber": data["chamber"],
                "district": data["district"],
                "party": data["party"],
                "samples": sample_count,
                "enrolled": sample_count > 0
            })
            
        return sorted(legislators, key=lambda x: (x["chamber"], int(x["district"])))


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Profile Manager")
    parser.add_argument("command", choices=["init", "status", "list", "get", "search", "committee"])
    parser.add_argument("--name", help="Legislator name for 'get' command")
    parser.add_argument("--query", help="Search query for 'search' command")
    parser.add_argument("--code", help="Committee code for 'committee' command")
    
    args = parser.parse_args()
    
    pm = ProfileManager()
    
    if args.command == "init":
        result = pm.initialize_database()
        print(f"✅ Database initialized:")
        print(f"   Created: {result['created']} profiles")
        print(f"   Skipped: {result['skipped']} (already exist)")
        print(f"   Total:   {result['total']} legislators")
        
    elif args.command == "status":
        status = pm.get_enrollment_status()
        print(f"📊 Enrollment Status:")
        print(f"   Total legislators: {status['total_legislators']}")
        print(f"   Enrolled:          {status['enrolled']}")
        print(f"   Not enrolled:      {status['not_enrolled']}")
        print(f"   Weak profiles:     {status['weak_profiles']}")
        
        if status['weak_profile_details']:
            print("\n⚠️  Weak profiles (< 3 samples):")
            for wp in status['weak_profile_details'][:10]:
                print(f"   - {wp['name']}: {wp['samples']} samples, {wp['time']:.1f}s")
                
    elif args.command == "list":
        legislators = pm.list_all_legislators()
        print(f"📋 All Legislators ({len(legislators)} total):\n")
        
        current_chamber = None
        for leg in legislators:
            if leg["chamber"] != current_chamber:
                current_chamber = leg["chamber"]
                print(f"\n{'='*40}")
                print(f"{current_chamber}")
                print(f"{'='*40}")
            
            status = "✓" if leg["enrolled"] else " "
            samples = f"({leg['samples']} samples)" if leg["enrolled"] else ""
            print(f"  [{status}] D{leg['district']:>2} ({leg['party'][0]}) {leg['name']} {samples}")
            
    elif args.command == "get":
        if not args.name:
            print("Error: --name required for 'get' command")
        else:
            profile = pm.get_profile(args.name)
            if profile:
                print(json.dumps(profile, indent=2))
            else:
                print(f"Profile not found: {args.name}")
                
    elif args.command == "search":
        if not args.query:
            print("Error: --query required for 'search' command")
        else:
            matches = pm.search_legislators(args.query)
            print(f"Found {len(matches)} matches for '{args.query}':")
            for name in matches:
                print(f"  - {name}")
                
    elif args.command == "committee":
        if not args.code:
            print("Error: --code required for 'committee' command")
        else:
            members = pm.get_committee_roster(args.code)
            print(f"Committee {args.code} ({len(members)} members):")
            for name in members:
                print(f"  - {name}")
