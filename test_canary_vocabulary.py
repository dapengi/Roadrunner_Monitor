#!/usr/bin/env python3
"""Test Canary custom vocabulary system."""

import sys
from pathlib import Path

# Add data directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data.canary_vocabulary import get_canary_vocabulary

def test_vocabulary():
    """Test vocabulary corrections and statistics."""
    
    print("="*70)
    print("CANARY CUSTOM VOCABULARY TEST")
    print("="*70)
    
    # Get vocabulary instance
    vocab = get_canary_vocabulary()
    
    # Show statistics
    print("\n📊 Vocabulary Statistics:")
    stats = vocab.get_statistics()
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    # Show context
    print("\n📖 Vocabulary Context String:")
    context = vocab.get_vocabulary_context()
    print(f"   {context}")
    
    # Test corrections
    print("\n✏️  Testing Vocabulary Corrections:")
    print("=" * 70)
    
    test_cases = [
        (
            "Original",
            "Senator fig aurora from alber quirky spoke about the lfc budget at sante fe.",
            "Should correct: fig aurora → Figueroa, alber quirky → Albuquerque, lfc → LFC, sante fe → Santa Fe"
        ),
        (
            "Surnames",
            "Representatives martinus, gonz ales, and roy bal testified.",
            "Should correct: martinus → Martinez, gonz ales → Gonzales, roy bal → Roybal"
        ),
        (
            "Committees",
            "The hafc and le sc committees met with s f c members.",
            "Should correct: hafc → HAFC, le sc → LESC, s f c → SFC"
        ),
        (
            "Counties",
            "The meeting covered bernalillo, dona anna, and rio arriba counties.",
            "Should correct proper capitalization and accents"
        ),
        (
            "Mixed",
            "Senator lou han from espanola discussed los crucis development at the legislative finance committee.",
            "Should correct: lou han → Lujan, espanola → Española, los crucis → Las Cruces"
        )
    ]
    
    corrections_made = 0
    for test_name, test_text, description in test_cases:
        corrected = vocab.correct_text(test_text)
        
        print(f"\n[{test_name}]")
        print(f"Note: {description}")
        print(f"Original:  {test_text}")
        print(f"Corrected: {corrected}")
        
        if corrected != test_text:
            corrections_made += 1
            print("✅ Corrections applied")
        else:
            print("ℹ️  No corrections needed")
    
    # Summary
    print("\n" + "="*70)
    print(f"🎉 TEST COMPLETE: {corrections_made}/{len(test_cases)} test cases had corrections applied")
    print("="*70)
    
    # Test adding custom terms
    print("\n🔧 Testing Custom Term Addition:")
    custom_terms = ["OpenAI", "ChatGPT", "Anthropic", "Claude"]
    vocab.add_custom_terms(custom_terms)
    print(f"   Added {len(custom_terms)} custom terms: {', '.join(custom_terms)}")
    
    # Test correction with custom terms
    test_with_custom = "The committee discussed open ai and chat gpt integration."
    corrected_custom = vocab.correct_text(test_with_custom)
    print(f"   Test: {test_with_custom}")
    print(f"   Result: {corrected_custom}")
    
    print("\n✅ Vocabulary system ready for use with Canary transcription!")

if __name__ == "__main__":
    test_vocabulary()
