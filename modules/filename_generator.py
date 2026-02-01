"""
Filename and path generator for legislative transcripts.
Handles naming conventions for interim vs session committees.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class FilenameGenerator:
    """Generates filenames and paths following legislative naming conventions."""
    
    # Committee acronym mappings
    COMMITTEE_ACRONYMS = {
        # House Committees
        "haawc": "HAAWC",
        "house agriculture": "HAAWC",
        "house agriculture acequias and water resources": "HAAWC",
        "hafc": "HAFC",
        "house appropriations": "HAFC",
        "house appropriations and finance": "HAFC",
        "hcedc": "HCEDC",
        "house commerce": "HCEDC",
        "house commerce and economic development": "HCEDC",
        "hcpac": "HCPAC",
        "house consumer": "HCPAC",
        "house consumer and public affairs": "HCPAC",
        "hec": "HEC",
        "house education": "HEC",
        "henrc": "HENRC",
        "house energy": "HENRC",
        "house energy environment and natural resources": "HENRC",
        "hgeic": "HGEIC",
        "house government": "HGEIC",
        "house government elections and indian affairs": "HGEIC",
        "hhhc": "HHHC",
        "house health": "HHHC",
        "house health and human services": "HHHC",
        "hjc": "HJC",
        "house judiciary": "HJC",
        "hlvmc": "HLVMC",
        "house labor": "HLVMC",
        "house labor veterans and military affairs": "HLVMC",
        "house rural development": "HRDLC",
        "house rural development land grants and cultural affairs": "HRDLC",
        "hrdlc": "HRDLC",
        "house transportation": "HTPWC",
        "house transportation public works and capital improvements": "HTPWC",
        "htpwc": "HTPWC",
        "house taxation": "HTRC",
        "house taxation and revenue": "HTRC",
        "htrc": "HTRC",
        "house rules": "HXRC",
        "house rules and order of business": "HXRC",
        "hxrc": "HXRC",

        # Senate Committees
        "sconc": "SCONC",
        "senate conservation": "SCONC",
        "sec": "SEC",
        "senate education": "SEC",
        "senate finance": "SFC",
        "sfc": "SFC",
        "senate health": "SHPAC",
        "senate health and public affairs": "SHPAC",
        "shpac": "SHPAC",
        "senate indian": "SIRC",
        "senate indian rural and cultural affairs": "SIRC",
        "sirc": "SIRC",
        "senate judiciary": "SJC",
        "sjc": "SJC",
        "senate rules": "SRC",
        "src": "SRC",
        "senate tax": "STBTC",
        "senate tax business and transportation": "STBTC",
        "stbtc": "STBTC",
        "senate committees committee": "SXCC",
        "sxcc": "SXCC",

        # Interim Committees
        "alc": "ALC",
        "legislative council": "ALC",
        "capitol buildings planning commission": "CBPC",
        "cbpc": "CBPC",
        "ccj": "CCJ",
        "courts corrections": "CCJ",
        "courts corrections and justice": "CCJ",
        "capitol security": "CSS",
        "capitol security subcommittee": "CSS",
        "css": "CSS",
        "economic and rural development": "ERDPC",
        "economic and rural development and policy": "ERDPC",
        "erdpc": "ERDPC",
        "facilities review": "FRS",
        "facilities review subcommittee": "FRS",
        "frs": "FRS",
        "haawc": "HAAWC",
        "hafc": "HAFC",
        "hcedc": "HCEDC",
        "hcpac": "HCPAC",
        "hec": "HEC",
        "henrc": "HENRC",
        "hgeic": "HGEIC",
        "hhhc": "HHHC",
        "hjc": "HJC",
        "hlvmc": "HLVMC",
        "hrdlc": "HRDLC",
        "htpwc": "HTPWC",
        "htrc": "HTRC",
        "hxrc": "HXRC",
        "iac": "IAC",
        "indian affairs": "IAC",
        "indian affairs committee": "IAC",
        "investments and pensions": "IPOC",
        "investments and pensions oversight": "IPOC",
        "ipoc": "IPOC",
        "interim legislative ethics": "LEC",
        "lec": "LEC",
        "legislative ethics committee": "LEC",
        "legislative education study": "LESC",
        "lesc": "LESC",
        "legislative finance": "LFC",
        "lfc": "LFC",
        "land grant": "LGC",
        "land grant committee": "LGC",
        "lgc": "LGC",
        "legislative health and human services": "LHHS",
        "lhhs": "LHHS",
        "mfa": "MFA",
        "mortgage finance authority": "MFA",
        "mortgage finance authority act oversight": "MFA",
        "military and veterans": "MVAC",
        "military and veterans affairs": "MVAC",
        "mvac": "MVAC",
        "new mexico finance authority": "NMFA",
        "new mexico finance authority oversight": "NMFA",
        "nmfa": "NMFA",
        "psco": "PSCO",
        "public school capital outlay": "PSCO",
        "public school capital outlay oversight": "PSCO",
        "radioactive and hazardous materials": "RHMC",
        "radioactive hazardous": "RHMC",
        "rhmc": "RHMC",
        "revenue stabilization": "RSTP",
        "revenue stabilization and tax policy": "RSTP",
        "rstp": "RSTP",
        "sconc": "SCONC",
        "sec": "SEC",
        "sfc": "SFC",
        "shpac": "SHPAC",
        "sirc": "SIRC",
        "sjc": "SJC",
        "src": "SRC",
        "stbtc": "STBTC",
        "science technology": "STTC",
        "science technology and telecommunications": "STTC",
        "sttc": "STTC",
        "sxcc": "SXCC",
        "tirs": "TIRS",
        "transportation infrastructure revenue": "TIRS",
        "transportation infrastructure revenue subcommittee": "TIRS",
        "tobacco settlement": "TSROC",
        "tobacco settlement revenue oversight": "TSROC",
        "tsroc": "TSROC",
        "water and natural resources": "WNR",
        "water natural resources": "WNR",
        "wnr": "WNR",
        "federal funding stabilization": "ZFFSS",
        "federal funding stabilization subcommittee": "ZFFSS",
        "zffss": "ZFFSS",
        "legislative interim committee working group": "ZLICW",
        "zlicw": "ZLICW",
    }
    
    def __init__(self):
        """Initialize filename generator."""
        pass
    
    def detect_session_type(self, title: str) -> str:
        """
        Detect if meeting is interim, house, or senate.
        
        Args:
            title: Meeting title
            
        Returns:
            'IC' for interim, 'HOUSE', or 'SENATE'
        """
        # Normalize hyphens and extra spaces for better matching
        title_lower = title.lower().replace(' - ', ' ').replace('-', ' ')
        
        # Check for explicit markers
        if 'interim' in title_lower or title_lower.startswith('ic '):
            return 'IC'
        
        if 'house' in title_lower:
            return 'HOUSE'
        
        if 'senate' in title_lower:
            return 'SENATE'
        
        # Default to interim if unclear
        logger.warning(f"Could not determine session type for: {title}, defaulting to IC")
        return 'IC'
    
    def extract_committee_acronym(self, title: str) -> str:
        """
        Extract committee acronym from meeting title.
        
        Args:
            title: Meeting title
            
        Returns:
            Committee acronym (e.g., 'LFC', 'HAFC', 'SJC')
        """
        # Normalize hyphens for acronym matching
        title_lower = title.lower().replace(" - ", " ").replace("-", " ")
        
        # Try to find known committee names
        for committee_name, acronym in self.COMMITTEE_ACRONYMS.items():
            if committee_name in title_lower:
                return acronym
        
        # Try to extract acronym if present (e.g., "IC - LFC" or "HAFC -")
        acronym_match = re.search(r'\b([A-Z]{2,5})\b', title)
        if acronym_match:
            potential_acronym = acronym_match.group(1)
            # Verify it's a known acronym
            if potential_acronym in self.COMMITTEE_ACRONYMS.values():
                return potential_acronym
        
        # Fallback: try to create acronym from title
        words = [w for w in title.split() if len(w) > 2 and w[0].isupper()]
        if words:
            acronym = ''.join(w[0] for w in words[:3])
            logger.warning(f"Generated acronym '{acronym}' from title: {title}")
            return acronym
        
        # Last resort
        logger.error(f"Could not extract committee from: {title}")
        return 'UNKNOWN'
    
    def extract_time_range(self, title: str, meeting_date: datetime) -> Tuple[str, str]:
        """
        Extract start and end times from meeting title or use defaults.
        
        Args:
            title: Meeting title
            meeting_date: Meeting datetime
            
        Returns:
            Tuple of (start_time, end_time) in format like '837AM', '1153AM'
        """
        # Try to find time range in title (e.g., "8:37 AM - 11:53 AM")
        time_pattern = r'(\d{1,2})[:\s]?(\d{2})\s*(AM|PM)\s*-\s*(\d{1,2})[:\s]?(\d{2})\s*(AM|PM)'
        match = re.search(time_pattern, title, re.IGNORECASE)
        
        if match:
            start_hour, start_min, start_ampm = match.group(1), match.group(2), match.group(3).upper()
            end_hour, end_min, end_ampm = match.group(4), match.group(5), match.group(6).upper()
            
            start_time = f"{start_hour}{start_min}{start_ampm}"
            end_time = f"{end_hour}{end_min}{end_ampm}"
            
            return start_time, end_time
        
        # Fallback: use meeting_date time
        start_time = meeting_date.strftime('%I%M%p').lstrip('0')  # Remove leading zero
        # Assume 2 hour duration
        end_datetime = meeting_date.replace(hour=(meeting_date.hour + 2) % 24)
        end_time = end_datetime.strftime('%I%M%p').lstrip('0')
        
        logger.info(f"Using inferred time range: {start_time}-{end_time}")
        return start_time, end_time
    
    def generate_filename(self, title: str, meeting_date: datetime) -> Dict[str, str]:
        """
        Generate filename following legislative convention.
        
        Format:
        - Interim: YYYYMMDD-IC-{COMMITTEE}-{START}-{END}
        - House: YYYYMMDD-HOUSE-{COMMITTEE}-{START}-{END}
        - Senate: YYYYMMDD-SENATE-{COMMITTEE}-{START}-{END}
        
        Args:
            title: Meeting title
            meeting_date: Meeting datetime
            
        Returns:
            Dict with 'base_name', 'session_type', 'committee'
        """
        # Get components
        session_type = self.detect_session_type(title)
        committee = self.extract_committee_acronym(title)
        start_time, end_time = self.extract_time_range(title, meeting_date)
        
        # Format date as YYYYMMDD
        date_str = meeting_date.strftime('%Y%m%d')
        
        # Build filename
        base_name = f"{date_str}-{session_type}-{committee}-{start_time}-{end_time}"
        
        logger.info(f"Generated filename: {base_name}")
        
        return {
            'base_name': base_name,
            'session_type': session_type,
            'committee': committee,
            'date': meeting_date.strftime('%Y-%m-%d'),
            'start_time': start_time,
            'end_time': end_time
        }
    
    def get_seafile_path(self, filename_info: Dict[str, str]) -> str:
        """
        Generate Seafile upload path based on session type.
        
        Interim: /Interim/{committee}/{yyyy-mm-dd}/captions/
        Session: /Session/{HOUSE|SENATE}/{committee}/{yyyy-mm-dd}/captions/
        
        Args:
            filename_info: Dict from generate_filename()
            
        Returns:
            Seafile upload path
        """
        session_type = filename_info['session_type']
        committee = filename_info['committee']
        date = filename_info['date']
        
        if session_type == 'IC':
            # Interim committee
            path = f"/Interim/{committee}/{date}/captions"
        else:
            # Session committee (House or Senate)
            path = f"/Session/{session_type}/{committee}/{date}/captions"
        
        return path
    
    def get_sftp_path(self) -> str:
        """
        Get SFTP upload path (flat structure).
        
        Returns:
            SFTP path
        """
        return "/private_html/inbound_uploads/ristra_data/incoming"


# Singleton instance
_generator = None

def get_filename_generator() -> FilenameGenerator:
    """Get or create singleton generator instance."""
    global _generator
    if _generator is None:
        _generator = FilenameGenerator()
    return _generator


if __name__ == "__main__":
    # Test the generator
    gen = get_filename_generator()
    
    print("Filename Generator Test")
    print("=" * 70)
    
    test_cases = [
        ("IC - Legislative Finance (Room 307)", datetime(2025, 11, 20, 8, 37)),
        ("HAFC - House Appropriations and Finance Committee", datetime(2025, 10, 1, 1, 27)),
        ("Senate Judiciary Committee Meeting", datetime(2025, 10, 1, 14, 16)),
        ("Interim - Water and Natural Resources", datetime(2025, 12, 15, 9, 0)),
    ]
    
    for title, meeting_date in test_cases:
        print(f"\nTitle: {title}")
        print(f"Date: {meeting_date}")
        
        info = gen.generate_filename(title, meeting_date)
        
        print(f"  Base Name: {info['base_name']}")
        print(f"  Session Type: {info['session_type']}")
        print(f"  Committee: {info['committee']}")
        print(f"  Seafile Path: {gen.get_seafile_path(info)}")
        print(f"  SFTP Path: {gen.get_sftp_path()}")
        print(f"  Full filenames:")
        print(f"    - {info['base_name']}.json")
        print(f"    - {info['base_name']}.csv")
        print(f"    - {info['base_name']}.txt")
