#!/usr/bin/env python3
"""
Legislative Caption Downloader - Interactive Version
Downloads closed captions from New Mexico Legislature Harmony/Sliq.net streaming system.
Uses command-line prompts for user input.
"""

import os
import sys
from caption_downloader import CaptionDownloader


class InteractiveCaptionDownloader:
    def __init__(self):
        self.downloader = CaptionDownloader()
        
    def print_banner(self):
        """Print welcome banner"""
        print("=" * 70)
        print("    NEW MEXICO LEGISLATURE CAPTION DOWNLOADER")
        print("=" * 70)
        print("This tool downloads closed captions from legislative videos.")
        print("Supported formats: TXT, VTT, SRT, CSV, JSON")
        print("-" * 70)
        
    def get_url_input(self):
        """Get URL from user via input prompt"""
        print("\n📺 VIDEO URL")
        print("Enter the New Mexico Legislature video URL.")
        print("Example: https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250819/-1/77483")
        print()
        
        while True:
            url = input("URL: ").strip()
            
            if not url:
                print("❌ Please enter a URL.")
                continue
                
            if "harmony.sliq.net" not in url.lower():
                print("⚠️  This doesn't appear to be a New Mexico Legislature URL.")
                continue_anyway = input("Continue anyway? (y/n): ").lower().strip()
                if continue_anyway not in ['y', 'yes']:
                    continue
                    
            return url
    
    def get_format_selection(self):
        """Get format selection from user"""
        print("\n📁 OUTPUT FORMATS")
        print("Select the output formats you want (enter numbers separated by commas):")
        print()
        
        formats = {
            '1': ('txt', 'Plain text transcript (easy to read)'),
            '2': ('vtt', 'WebVTT format (for web video players)'),
            '3': ('srt', 'SubRip format (for video editing software)'),
            '4': ('csv', 'CSV with timestamps (for data analysis)'),
            '5': ('json', 'JSON format (raw data with metadata)'),
            '6': ('all', 'All formats above')
        }
        
        for key, (fmt, description) in formats.items():
            print(f"  {key}. {fmt.upper()} - {description}")
        
        print()
        print("Examples:")
        print("  Enter '1' for just TXT")
        print("  Enter '1,2' for TXT and VTT")
        print("  Enter '6' for all formats")
        print()
        
        while True:
            selection = input("Your choice: ").strip()
            
            if not selection:
                print("❌ Please enter at least one number.")
                continue
            
            # Parse selection
            try:
                choices = [choice.strip() for choice in selection.split(',')]
                selected_formats = []
                
                for choice in choices:
                    if choice == '6':  # All formats
                        return ['txt', 'vtt', 'srt', 'csv', 'json']
                    elif choice in formats and choice != '6':
                        fmt_name = formats[choice][0]
                        if fmt_name not in selected_formats:
                            selected_formats.append(fmt_name)
                    else:
                        print(f"❌ Invalid choice: {choice}")
                        break
                else:
                    if selected_formats:
                        return selected_formats
                        
            except Exception:
                print("❌ Invalid input. Please enter numbers separated by commas.")
    
    def get_output_directory(self):
        """Get output directory from user"""
        print("\n📂 OUTPUT DIRECTORY")
        print("Where would you like to save the caption files?")
        print(f"Current directory: {os.getcwd()}")
        print()
        print("Options:")
        print("  1. Current directory (default)")
        print("  2. Enter custom path")
        print()
        
        while True:
            choice = input("Your choice (1 or 2): ").strip()
            
            if choice == '1' or choice == '':
                return os.getcwd()
            elif choice == '2':
                while True:
                    custom_path = input("Enter directory path: ").strip()
                    if os.path.exists(custom_path):
                        return custom_path
                    else:
                        print(f"❌ Directory doesn't exist: {custom_path}")
                        create = input("Create this directory? (y/n): ").lower().strip()
                        if create in ['y', 'yes']:
                            try:
                                os.makedirs(custom_path, exist_ok=True)
                                return custom_path
                            except Exception as e:
                                print(f"❌ Error creating directory: {e}")
                        else:
                            break
            else:
                print("❌ Please enter 1 or 2.")
    
    def run(self):
        """Main interactive flow"""
        try:
            while True:
                self.print_banner()
                
                # Get URL
                url = self.get_url_input()
                
                # Get formats
                formats = self.get_format_selection()
                
                # Get output directory
                output_dir = self.get_output_directory()
                
                # Confirm selection
                print("\n✅ DOWNLOAD SUMMARY")
                print("-" * 30)
                print(f"URL: {url}")
                print(f"Formats: {', '.join([f.upper() for f in formats])}")
                print(f"Output: {output_dir}")
                print()
                
                confirm = input("Start download? (y/n): ").lower().strip()
                if confirm not in ['y', 'yes']:
                    print("❌ Download cancelled.")
                    break
                
                # Download captions
                print("\n⬇️  DOWNLOADING...")
                print("Fetching video page and extracting captions...")
                
                success = self.downloader.download_captions(url, formats, output_dir)
                
                if success:
                    print("\n🎉 SUCCESS!")
                    print("=" * 50)
                    print("Captions downloaded successfully!")
                    print(f"Files saved to: {output_dir}")
                    print()
                    
                    # List created files
                    print("📄 Files created:")
                    for fmt in formats:
                        # Generate expected filename
                        try:
                            # This is a simplified filename generation
                            url_parts = url.split('/')
                            date_part = ""
                            id_part = ""
                            
                            for part in url_parts:
                                if len(part) == 8 and part.isdigit():
                                    date_part = part
                                elif part.isdigit():
                                    id_part = part
                            
                            filename = f"legislative_captions_{date_part}_{id_part}.{fmt}"
                            filepath = os.path.join(output_dir, filename)
                            
                            if os.path.exists(filepath):
                                file_size = os.path.getsize(filepath)
                                print(f"  ✓ {filename} ({file_size:,} bytes)")
                            else:
                                # Try to find any file with this extension
                                for file in os.listdir(output_dir):
                                    if file.endswith(f".{fmt}"):
                                        file_size = os.path.getsize(os.path.join(output_dir, file))
                                        print(f"  ✓ {file} ({file_size:,} bytes)")
                                        break
                        except:
                            print(f"  ✓ {fmt.upper()} file created")
                    
                else:
                    print("\n❌ DOWNLOAD FAILED")
                    print("=" * 50)
                    print("Failed to download captions. This could be because:")
                    print("• The URL is invalid or inaccessible")
                    print("• The video doesn't have captions")
                    print("• Network connection issues")
                    print("• The video format is not supported")
                
                # Ask if user wants to continue
                print("\n" + "=" * 50)
                another = input("Download captions from another video? (y/n): ").lower().strip()
                if another not in ['y', 'yes']:
                    break
                    
                print("\n")  # Extra spacing for next iteration
                
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled by user.")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        print("\n👋 Thank you for using the Caption Downloader!")


def main():
    """Main entry point"""
    app = InteractiveCaptionDownloader()
    app.run()


if __name__ == "__main__":
    main()