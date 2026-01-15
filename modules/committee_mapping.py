# data/committee_mapping.py

"""
Committee name mapping and meeting title parsing functions
"""

import re
import logging
from config import NEXTCLOUD_BASE_FOLDER # <--- THIS LINE MUST BE AT THE TOP

logger = logging.getLogger(__name__)


def _clean_committee_text(text):
    """
    Cleans committee text by removing common extraneous words and standardizing.
    """
    # Remove text in parentheses
    text = re.sub(r'\([^)]*\)', '', text)
    # Remove common meeting status/type words
    text = re.sub(r'\b(Adjourned|Committee|Meeting|Session|Subcommittee|Council|Task Force|Oversight)\b', '', text, flags=re.IGNORECASE)
    # Replace common conjunctions for standardization
    text = text.replace('&', 'and')
    # Remove non-alphanumeric characters except spaces and hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    # Standardize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower() # Return in lowercase for consistent matching


def get_committee_acronyms():
    """Return mapping of committee names to their acronyms."""
    return {
        # Interim Committees
        'Capitol Buildings Planning': 'CBP',
        'Capitol Security': 'CS',
        'Courts, Corrections & Justice': 'CCJ',
        'Economic & Rural Development & Policy': 'ERDP',
        'Economic and Rural Development and Policy': 'ERDP',
        'Federal Funding Stabilization': 'FFS',
        'Indian Affairs': 'IA',
        'Interim Legislative Ethics': 'ILE',
        'Investments & Pensions Oversight': 'IPO',
        'Investments and Pensions Oversight': 'IPO',
        'Land Grant': 'LG',
        'Legislative Council': 'LC',
        'Legislative Education Study': 'LES',
        'Legislative Finance': 'LFC',
        'Legislative Health & Human Services': 'LHHS',
        'Legislative Health and Human Services': 'LHHS',
        'Military & Veterans\' Affairs': 'MVA',
        'Military and Veterans\' Affairs': 'MVA',
        'Mortgage Finance Authority Act Oversight': 'MFAAO',
        'New Mexico Finance Authority Oversight': 'NMFAO',
        'Public School Capital Outlay Oversight': 'PSCOO',
        'Radioactive & Hazardous Materials': 'RHM',
        'Radioactive and Hazardous Materials': 'RHM',
        'Revenue Stabilization & Tax Policy': 'RSTP',
        'Revenue Stabilization and Tax Policy': 'RSTP',
        'Science, Technology & Telecommunications': 'STT',
        'Science, Technology and Telecommunications': 'STT',
        'Tobacco Settlement Revenue Oversight': 'TSRO',
        'Transportation Infrastructure Revenue': 'TIR',
        'Water & Natural Resources': 'WNRC',
        'Water and Natural Resources': 'WNRC',
        
        # House Committees
        'Agriculture, Acequias And Water Resources': 'AAWR',
        'Appropriations & Finance': 'AF',
        'Commerce & Economic Development Committee': 'CEDC',
        'Consumer & Public Affairs': 'CPA',
        'Education': 'ED',
        'Energy, Environment & Natural Resources': 'EENR',
        'Government, Elections & Indian Affairs': 'GEIA',
        'Health & Human Services': 'HHS',
        'Judiciary': 'JUD',
        'Labor, Veterans\' And Military Affairs Committee': 'LVMAC',
        'Rules & Order Of Business': 'ROB',
        'Rural Development, Land Grants And Cultural Affairs': 'RDLGCA',
        'Taxation & Revenue': 'TR',
        'Transportation, Public Works & Capital Improvements': 'TPWCI',
        
        # Senate Committees
        'Committees\' Committee': 'CC',
        'Conservation': 'CON',
        'Finance': 'FIN',
        'Health & Public Affairs': 'HPA',
        'Indian, Rural & Cultural Affairs': 'IRCA',
        'Rules': 'RULES',
        'Tax, Business & Transportation': 'TBT'
    }


def get_committee_acronym(committee_name):
    """Get the acronym for a committee name."""
    acronyms = get_committee_acronyms()
    
    # Clean the input committee name for matching
    cleaned_committee_name = _clean_committee_text(committee_name)
    
    # Try exact match first (after cleaning)
    for full_name, acronym in acronyms.items():
        if _clean_committee_text(full_name) == cleaned_committee_name:
            return acronym
    
    # If no exact match, try fuzzy matching with word overlap
    cleaned_words = set(cleaned_committee_name.split())
    
    best_match_acronym = None
    max_common_words = 0
    
    for full_name, acronym in acronyms.items():
        roster_words = set(_clean_committee_text(full_name).split())
        common_words = len(cleaned_words.intersection(roster_words))
        
        if common_words > max_common_words:
            max_common_words = common_words
            best_match_acronym = acronym
        elif common_words == max_common_words and best_match_acronym is None:
            # If multiple have same max, pick the first one encountered
            best_match_acronym = acronym

    if best_match_acronym and max_common_words >= 1: # At least one word matches
        logger.info(f"Fuzzy matched '{committee_name}' to an acronym: {best_match_acronym} (common words: {max_common_words})")
        return best_match_acronym
    
    # If no match found, create a simple acronym from the name
    words = cleaned_committee_name.split()
    # Take first letter of each significant word (skip short words like 'and', 'of', 'the')
    significant_words = [w for w in words if len(w) > 2 or w in ['ic', 'us', 'nm']]
    simple_acronym = ''.join([w[0].upper() for w in significant_words[:4]])  # Max 4 letters
    
    if not simple_acronym: # Fallback if no significant words
        simple_acronym = "UNK"
        
    logger.warning(f"No specific acronym found for '{committee_name}', using generated: {simple_acronym}")
    return simple_acronym


def get_clean_committee_mapping():
    """Return mapping of committee names for clean folder/file naming."""
    # This function was missing, now it's defined.
    # It provides a mapping from cleaned, lowercased committee names
    # to their preferred full names for consistent display and folder paths.
    return {
        'interim': {
            _clean_committee_text('Capitol Buildings Planning'): 'Capitol Buildings Planning',
            _clean_committee_text('Capitol Security'): 'Capitol Security',
            _clean_committee_text('Courts, Corrections & Justice'): 'Courts, Corrections & Justice',
            _clean_committee_text('Economic & Rural Development & Policy'): 'Economic & Rural Development & Policy',
            _clean_committee_text('Economic and Rural Development and Policy'): 'Economic & Rural Development & Policy',
            _clean_committee_text('Facilities Review'): 'Facilities Review',
            _clean_committee_text('Federal Funding Stabilization'): 'Federal Funding Stabilization',
            _clean_committee_text('Indian Affairs'): 'Indian Affairs',
            _clean_committee_text('Interim Legislative Ethics'): 'Interim Legislative Ethics',
            _clean_committee_text('Legislative Ethics'): 'Interim Legislative Ethics',
            _clean_committee_text('Investments & Pensions Oversight'): 'Investments & Pensions Oversight',
            _clean_committee_text('Investments and Pensions Oversight'): 'Investments & Pensions Oversight',
            _clean_committee_text('Land Grant'): 'Land Grant',
            _clean_committee_text('Legislative Council'): 'Legislative Council',
            _clean_committee_text('Legislative Education Study'): 'Legislative Education Study',
            _clean_committee_text('Legislative Finance'): 'Legislative Finance',
            _clean_committee_text('Legislative Interim Committee Working Group'): 'Legislative Interim Committee Working Group',
            _clean_committee_text('Legislative Health & Human Services'): 'Legislative Health & Human Services',
            _clean_committee_text('Legislative Health and Human Services'): 'Legislative Health & Human Services',
            _clean_committee_text('Military & Veterans\' Affairs'): 'Military & Veterans\' Affairs',
            _clean_committee_text('Military and Veterans\' Affairs'): 'Military & Veterans\' Affairs',
            _clean_committee_text('Mortgage Finance Authority Act Oversight'): 'Mortgage Finance Authority Act Oversight',
            _clean_committee_text('Mortgage Finance Authority Oversight'): 'Mortgage Finance Authority Act Oversight',
            _clean_committee_text('New Mexico Finance Authority Oversight'): 'New Mexico Finance Authority Oversight',
            _clean_committee_text('Public School Capital Outlay Oversight'): 'Public School Capital Outlay Oversight',
            _clean_committee_text('Public School Capital Outlay Council'): 'Public School Capital Outlay Oversight',
            _clean_committee_text('Public School Capital Outlay Oversight Task'): 'Public School Capital Outlay Oversight',
            _clean_committee_text('Radioactive & Hazardous Materials'): 'Radioactive & Hazardous Materials',
            _clean_committee_text('Radioactive and Hazardous Materials'): 'Radioactive & Hazardous Materials',
            _clean_committee_text('Revenue Stabilization & Tax Policy'): 'Revenue Stabilization & Tax Policy',
            _clean_committee_text('Revenue Stabilization and Tax Policy'): 'Revenue Stabilization & Tax Policy',
            _clean_committee_text('Science, Technology & Telecommunications'): 'Science, Technology & Telecommunications',
            _clean_committee_text('Science, Technology and Telecommunications'): 'Science, Technology and Telecommunications',
            _clean_committee_text('Tobacco Settlement Revenue Oversight'): 'Tobacco Settlement Revenue Oversight',
            _clean_committee_text('Transportation Infrastructure Revenue'): 'Transportation Infrastructure Revenue',
            _clean_committee_text('Transportation Infrastructure Revenue Subcommittee'): 'Transportation Infrastructure Revenue',
            _clean_committee_text('Water & Natural Resources'): 'Water & Natural Resources',
            _clean_committee_text('Water and Natural Resources'): 'Water & Natural Resources'
        },
        'house': {
            _clean_committee_text('Agriculture, Acequias And Water Resources'): 'Agriculture, Acequias And Water Resources',
            _clean_committee_text('Appropriations & Finance'): 'Appropriations & Finance',
            _clean_committee_text('Commerce & Economic Development Committee'): 'Commerce & Economic Development Committee',
            _clean_committee_text('Consumer & Public Affairs'): 'Consumer & Public Affairs',
            _clean_committee_text('Education'): 'Education',
            _clean_committee_text('Energy, Environment & Natural Resources'): 'Energy, Environment & Natural Resources',
            _clean_committee_text('Government, Elections & Indian Affairs'): 'Government, Elections & Indian Affairs',
            _clean_committee_text('Health & Human Services'): 'Health & Human Services',
            _clean_committee_text('Judiciary'): 'Judiciary',
            _clean_committee_text('Labor, Veterans\' And Military Affairs Committee'): 'Labor, Veterans\' And Military Affairs Committee',
            _clean_committee_text('Rules & Order Of Business'): 'Rules & Order Of Business',
            _clean_committee_text('Rural Development, Land Grants And Cultural Affairs'): 'Rural Development, Land Grants And Cultural Affairs',
            _clean_committee_text('Taxation & Revenue'): 'Taxation & Revenue',
            _clean_committee_text('Taxation & Revenue'): 'Taxation & Revenue',
            _clean_committee_text('Transportation, Public Works & Capital Improvements'): 'Transportation, Public Works & Capital Improvements'
        },
        'senate': {
            _clean_committee_text('Committees\' Committee'): 'Committees\' Committee',
            _clean_committee_text('Conservation'): 'Conservation',
            _clean_committee_text('Education'): 'Education',
            _clean_committee_text('Finance'): 'Finance',
            _clean_committee_text('Health & Public Affairs'): 'Health & Public Affairs',
            _clean_committee_text('Indian, Rural & Cultural Affairs'): 'Indian, Rural & Cultural Affairs',
            _clean_committee_text('Judiciary'): 'Judiciary',
            _clean_committee_text('Rules'): 'Rules',
            _clean_committee_text('Tax, Business & Transportation'): 'Tax, Business & Transportation'
        }
    }


def parse_meeting_title(title):
    """Parse meeting title to determine folder structure and clean title."""
    try:
        # Clean up the title first - remove extra whitespace and newlines
        clean_title_raw = re.sub(r'\s+', ' ', title).strip()
        
        # Split on the first " - " to get prefix and committee name
        if ' - ' in clean_title_raw:
            prefix, committee_text_raw = clean_title_raw.split(' - ', 1)
            prefix = prefix.strip().upper()
            committee_text_raw = committee_text_raw.strip()
            
            # Clean committee text using the new helper function
            committee_for_matching = _clean_committee_text(committee_text_raw)
            
            # Get committee mapping
            committee_mapping = get_clean_committee_mapping()
            
            clean_committee_name = None
            committee_type = None
            
            if prefix == 'IC':
                committee_type = 'interim'
                
                # Try to find a matching committee using the cleaned text
                for key, value in committee_mapping['interim'].items():
                    if key == committee_for_matching:
                        clean_committee_name = value
                        logger.info(f"Found exact match for interim committee: '{committee_text_raw}' -> '{value}'")
                        break
                
                if not clean_committee_name:
                    # Fallback to fuzzy matching with word overlap if no exact match
                    cleaned_words = set(committee_for_matching.split())
                    best_match_name = None
                    max_common_words = 0
                    
                    for key, value in committee_mapping['interim'].items():
                        mapping_words = set(key.split())
                        common_words = len(cleaned_words.intersection(mapping_words))
                        if common_words > max_common_words:
                            max_common_words = common_words
                            best_match_name = value
                    
                    if best_match_name and max_common_words >= 1: # At least one word matches
                        clean_committee_name = best_match_name
                        logger.info(f"Fuzzy matched interim committee: '{committee_text_raw}' to '{clean_committee_name}' (common words: {max_common_words})")
                
                if clean_committee_name:
                    acronym = get_committee_acronym(clean_committee_name)
                    return {
                        'type': 'interim',
                        'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Interim/{acronym}",
                        'committee_name': clean_committee_name,
                        'committee_acronym': acronym,
                        'chamber': None,
                        'clean_title': f"IC - {clean_committee_name}",
                        'prefix': prefix
                    }
                else:
                    logger.warning(f"No specific match found for interim committee '{committee_text_raw}', using fallback to ERROR folder.")
                    # Fallback to ERROR if no good match
                    fallback_acronym = get_committee_acronym(committee_text_raw) # Use raw text for fallback acronym
                    return {
                        'type': 'error',
                        'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Other/ERROR",
                        'committee_name': committee_text_raw, # Keep original for error logging
                        'committee_acronym': fallback_acronym,
                        'chamber': None,
                        'clean_title': clean_title_raw,
                        'prefix': 'ERROR'
                    }
                    
            elif prefix in ['HOUSE', 'SENATE']:
                chamber = prefix.title()
                committee_type = chamber.lower()
                
                # Try to find a matching committee using the cleaned text
                for key, value in committee_mapping[committee_type].items():
                    if key == committee_for_matching:
                        clean_committee_name = value
                        logger.info(f"Found exact match for {chamber} committee: '{committee_text_raw}' -> '{value}'")
                        break
                
                if not clean_committee_name:
                    # Fallback to fuzzy matching with word overlap if no exact match
                    cleaned_words = set(committee_for_matching.split())
                    best_match_name = None
                    max_common_words = 0
                    
                    for key, value in committee_mapping[committee_type].items():
                        mapping_words = set(key.split())
                        common_words = len(cleaned_words.intersection(mapping_words))
                        if common_words > max_common_words:
                            max_common_words = common_words
                            best_match_name = value
                    
                    if best_match_name and max_common_words >= 1:
                        clean_committee_name = best_match_name
                        logger.info(f"Fuzzy matched {chamber} committee: '{committee_text_raw}' to '{clean_committee_name}' (common words: {max_common_words})")
                
                if clean_committee_name:
                    acronym = get_committee_acronym(clean_committee_name)
                    return {
                        'type': 'session',
                        'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/LegSession/{chamber}/{acronym}",
                        'committee_name': clean_committee_name,
                        'committee_acronym': acronym,
                        'chamber': chamber,
                        'clean_title': f"{chamber} - {clean_committee_name}",
                        'prefix': prefix
                    }
                else:
                    logger.warning(f"No specific match found for {chamber} committee '{committee_text_raw}', using fallback to ERROR folder.")
                    # Fallback to ERROR if no good match
                    fallback_acronym = get_committee_acronym(committee_text_raw)
                    return {
                        'type': 'error',
                        'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Other/ERROR",
                        'committee_name': committee_text_raw,
                        'committee_acronym': fallback_acronym,
                        'chamber': chamber,
                        'clean_title': clean_title_raw,
                        'prefix': 'ERROR'
                    }
            
            # If prefix is not IC, HOUSE, or SENATE
            logger.warning(f"Unrecognized prefix '{prefix}' in title '{clean_title_raw}', using fallback to ERROR folder.")
            fallback_acronym = get_committee_acronym(committee_text_raw)
            return {
                'type': 'error',
                'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Other/ERROR",
                'committee_name': committee_text_raw,
                'committee_acronym': fallback_acronym,
                'chamber': None,
                'clean_title': clean_title_raw,
                'prefix': 'ERROR'
            }
        else:
            # No " - " separator found, use default error structure
            logger.warning(f"Could not parse meeting title format (no ' - '): {clean_title_raw[:50]}..., using fallback to ERROR folder.")
            clean_committee = _clean_committee_text(clean_title_raw)
            committee_acronym = get_committee_acronym(clean_committee or 'Unknown')
            
            return {
                'type': 'error',
                'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Other/ERROR",
                'committee_name': clean_committee or 'Unknown Committee',
                'committee_acronym': committee_acronym,
                'chamber': None,
                'clean_title': clean_title_raw,
                'prefix': 'ERROR'
            }
            
    except Exception as e:
        logger.error(f"Critical error parsing meeting title '{title[:100]}...': {e}")
        # Ensure NEXTCLOUD_BASE_FOLDER is available even if other parts of parsing fail
        return {
            'type': 'error',
            'folder_path': f"{NEXTCLOUD_BASE_FOLDER}/Other/ERROR",
            'committee_name': 'Unknown Committee',
            'committee_acronym': 'ERROR',
            'chamber': None,
            'clean_title': title,
            'prefix': 'ERROR'
        }


