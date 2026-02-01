#!/usr/bin/env python3
"""
Test script to preview the email HTML with improved logo
"""

import sys
import os
import datetime
import tempfile
import webbrowser
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def generate_test_email_preview():
    """Generate a test email preview with sample data."""
    
    # Import the HTML template from notifications.py
    from modules.notifications import send_notification
    
    # Read the HTML template from the file
    with open('/Users/minimac/legislature-monitor/modules/notifications.py', 'r') as f:
        content = f.read()
    
    # Extract the HTML template
    start_marker = "html_template = '''<!DOCTYPE html"
    end_marker = "</html>'''"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        # Extract the HTML template
        template_start = content.find("'''", start_idx) + 3
        html_template = content[template_start:end_idx + 7]
        
        # Sample data for testing
        sample_data = {
            'COMMITTEE_NAME': 'Water and Natural Resources',
            'MEETING_DATE': 'Monday, August 18, 2025',
            'MEETING_TIME': '1:25 PM - 5:30 PM',
            'STATUS': 'Transcription Complete & Available',
            'VIDEO_SOURCE_URL': 'https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250522/-1/77483',
            'PROCESSING_TIME': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S MST'),
            'NEXTCLOUD_LINK': 'https://cloud.dapengi.party/s/i7JwGFGaYwx2Tj3'
        }
        
        # Replace placeholders with sample data
        html_content = html_template
        for key, value in sample_data.items():
            html_content = html_content.replace('{' + key + '}', value)
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        print("📧 Email Preview Generated!")
        print("=" * 50)
        print(f"Preview file: {temp_file_path}")
        print()
        print("🖼️  Logo Improvements:")
        print("  ✅ Changed from WebP to PNG format")
        print("  ✅ Reduced size to 180x47 pixels")
        print("  ✅ Added better email client compatibility")
        print("  ✅ Improved alt text for accessibility")
        print("  ✅ Added padding and centering")
        print()
        print("🌐 Opening preview in browser...")
        
        # Open in default browser
        webbrowser.open('file://' + temp_file_path)
        
        return temp_file_path
    else:
        print("❌ Could not extract HTML template from notifications.py")
        return None

def show_image_comparison():
    """Show comparison between old and new image URLs."""
    
    print("\n🔄 Image URL Comparison:")
    print("=" * 50)
    
    old_url = "https://res.cloudinary.com/dah7l8ct2/image/upload/v1753387743/logo_vqok6w.webp"
    new_url = "https://res.cloudinary.com/dah7l8ct2/image/upload/f_png,w_360,h_94,c_fit,q_85/v1753387743/logo_vqok6w.png"
    
    print("❌ OLD (problematic):")
    print(f"   {old_url}")
    print("   Issues: WebP format, large size (256x67), poor email support")
    print()
    print("✅ NEW (improved):")
    print(f"   {new_url}")
    print("   Benefits: PNG format, optimized size (180x47), better email compatibility")
    print()
    print("🔧 Cloudinary transformations applied:")
    print("   • f_png - Convert to PNG format")
    print("   • w_360,h_94 - Resize to 360x94 (2x for retina, displayed as 180x47)")
    print("   • c_fit - Maintain aspect ratio")
    print("   • q_85 - 85% quality for good balance")

if __name__ == "__main__":
    preview_path = generate_test_email_preview()
    show_image_comparison()
    
    if preview_path:
        print(f"\n📁 Preview file saved at: {preview_path}")
        print("💡 You can also open this file directly in any browser to see the email")
        
        # Keep the file around for manual inspection
        input("\nPress Enter to clean up the temporary file...")
        try:
            os.unlink(preview_path)
            print("🗑️  Temporary file cleaned up")
        except:
            print("⚠️  Could not clean up temporary file, but it will be removed by system eventually")