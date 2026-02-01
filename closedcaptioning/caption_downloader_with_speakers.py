#!/usr/bin/env python3
"""
Caption Downloader with Speaker Detection
Downloads captions and automatically detects speaker changes for better readability.
"""

import os
import sys
from caption_downloader import CaptionDownloader
from enhanced_speaker_detection import EnhancedSpeakerDetector


class CaptionDownloaderWithSpeakers:
    def __init__(self):
        self.caption_downloader = CaptionDownloader()
        self.speaker_detector = EnhancedSpeakerDetector()
        
    def print_banner(self):
        """Print welcome banner"""
        print("=" * 70)
        print("    LEGISLATIVE CAPTION DOWNLOADER WITH SPEAKER DETECTION")
        print("=" * 70)
        print("Downloads captions and automatically identifies speaker changes")
        print("for improved readability of legislative transcripts.")
        print("-" * 70)
        
    def get_url_input(self):
        """Get URL from user"""
        print("\n📺 VIDEO URL")
        print("Enter the New Mexico Legislature video URL:")
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
    
    def get_output_options(self):
        """Get output format preferences"""
        print("\n📁 OUTPUT OPTIONS")
        print("What would you like to create?")
        print()
        print("1. Speaker-segmented transcript (recommended)")
        print("2. Traditional caption formats (VTT, SRT, etc.)")
        print("3. Both speaker transcript and caption formats")
        print("4. Raw captions only (no speaker detection)")
        print()
        
        while True:
            choice = input("Your choice (1-4): ").strip()
            
            if choice == '1':
                return 'speakers_only', []
            elif choice == '2':
                formats = self.get_caption_formats()
                return 'captions_only', formats
            elif choice == '3':
                formats = self.get_caption_formats()
                return 'both', formats
            elif choice == '4':
                formats = self.get_caption_formats()
                return 'raw_only', formats
            else:
                print("❌ Please enter 1, 2, 3, or 4.")
    
    def get_caption_formats(self):
        """Get traditional caption formats"""
        print("\nSelect caption formats (enter numbers separated by commas):")
        print("1. TXT - Plain text transcript")
        print("2. VTT - WebVTT (for web players)")
        print("3. SRT - SubRip (for video editing)")
        print("4. CSV - Data with timestamps")
        print("5. JSON - Raw data")
        print("6. All formats")
        print()
        
        while True:
            selection = input("Formats: ").strip()
            
            formats_map = {
                '1': 'txt', '2': 'vtt', '3': 'srt', 
                '4': 'csv', '5': 'json'
            }
            
            if selection == '6':
                return ['txt', 'vtt', 'srt', 'csv', 'json']
            
            try:
                choices = [choice.strip() for choice in selection.split(',')]
                selected_formats = []
                
                for choice in choices:
                    if choice in formats_map:
                        fmt = formats_map[choice]
                        if fmt not in selected_formats:
                            selected_formats.append(fmt)
                    else:
                        print(f"❌ Invalid choice: {choice}")
                        break
                else:
                    if selected_formats:
                        return selected_formats
                        
            except Exception:
                print("❌ Invalid input. Please enter numbers separated by commas.")
    
    def get_output_directory(self):
        """Get output directory"""
        print("\n📂 OUTPUT DIRECTORY")
        current_dir = os.getcwd()
        print(f"Current directory: {current_dir}")
        print()
        
        use_current = input("Save files here? (y/n): ").lower().strip()
        if use_current in ['y', 'yes', '']:
            return current_dir
        
        while True:
            custom_path = input("Enter directory path: ").strip()
            if os.path.exists(custom_path):
                return custom_path
            else:
                create = input(f"Create directory '{custom_path}'? (y/n): ").lower().strip()
                if create in ['y', 'yes']:
                    try:
                        os.makedirs(custom_path, exist_ok=True)
                        return custom_path
                    except Exception as e:
                        print(f"❌ Error creating directory: {e}")
                else:
                    continue
    
    def generate_base_filename(self, url, metadata):
        """Generate base filename from URL and metadata"""
        # Extract components from URL
        url_parts = url.split('/')
        date_part = ""
        id_part = ""
        
        for part in url_parts:
            if len(part) == 8 and part.isdigit():
                date_part = part
            elif part.isdigit():
                id_part = part
        
        # Use title if available
        if metadata.get('og_title'):
            import re
            title = re.sub(r'[^\w\s-]', '', metadata['og_title'])[:40]
            title = re.sub(r'\s+', '_', title)
        else:
            title = "legislative_transcript"
        
        return f"{title}_{date_part}_{id_part}"
    
    def run(self):
        """Main execution flow"""
        try:
            self.print_banner()
            
            # Get URL
            url = self.get_url_input()
            
            # Get output preferences
            output_type, caption_formats = self.get_output_options()
            
            # Get output directory
            output_dir = self.get_output_directory()
            
            print("\n⬇️  DOWNLOADING AND PROCESSING...")
            print("Fetching video page and extracting captions...")
            
            # Download captions using original downloader
            html_content = self.caption_downloader.fetch_page(url)
            if not html_content:
                print("❌ Failed to fetch video page.")
                return False
            
            # Extract captions
            caption_data = self.caption_downloader.extract_captions(html_content)
            if not caption_data:
                print("❌ No captions found.")
                return False
            
            # Extract metadata
            metadata = self.caption_downloader.extract_metadata(html_content)
            
            # Get English captions
            captions = caption_data.get('en', [])
            if not captions:
                print("❌ No English captions found.")
                return False
            
            print(f"Found {len(captions)} caption segments")
            
            # Generate base filename
            base_filename = self.generate_base_filename(url, metadata)
            
            files_created = []
            
            # Process based on user choice
            if output_type in ['speakers_only', 'both']:
                print("🎯 Detecting speakers...")
                
                segments = self.speaker_detector.detect_speakers(captions)
                
                print(f"Detected {len(segments)} speaker segments")
                
                # Export speaker transcript
                transcript_file = os.path.join(output_dir, f"{base_filename}_speakers.txt")
                self.speaker_detector.export_readable_transcript(segments, transcript_file)
                files_created.append(('Speaker Transcript', transcript_file))
                
                # Export speaker data
                speaker_csv = os.path.join(output_dir, f"{base_filename}_speaker_data.csv")
                self.speaker_detector.export_speaker_csv(segments, speaker_csv)
                files_created.append(('Speaker Data', speaker_csv))
                
                # Generate and save summary
                summary = self.speaker_detector.generate_summary(segments)
                summary_file = os.path.join(output_dir, f"{base_filename}_speaker_summary.txt")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                files_created.append(('Speaker Summary', summary_file))
            
            if output_type in ['captions_only', 'both', 'raw_only']:
                print("📝 Creating caption files...")
                
                for fmt in caption_formats:
                    filepath = os.path.join(output_dir, f"{base_filename}.{fmt}")
                    
                    try:
                        if fmt == 'vtt':
                            self.caption_downloader.save_as_webvtt(captions, filepath)
                        elif fmt == 'srt':
                            self.caption_downloader.save_as_srt(captions, filepath)
                        elif fmt == 'txt':
                            self.caption_downloader.save_as_txt(captions, filepath)
                        elif fmt == 'csv':
                            self.caption_downloader.save_as_csv(captions, filepath)
                        elif fmt == 'json':
                            self.caption_downloader.save_as_json(captions, filepath)
                        
                        files_created.append((f'{fmt.upper()} Caption', filepath))
                        
                    except Exception as e:
                        print(f"❌ Error creating {fmt}: {e}")
            
            # Success summary
            print("\n🎉 SUCCESS!")
            print("=" * 50)
            print("Files created:")
            
            for file_type, filepath in files_created:
                file_size = os.path.getsize(filepath)
                filename = os.path.basename(filepath)
                print(f"  ✓ {file_type}: {filename} ({file_size:,} bytes)")
            
            print(f"\n📁 All files saved to: {output_dir}")
            
            if output_type in ['speakers_only', 'both']:
                print("\n🎯 SPEAKER DETECTION RESULTS")
                print("-" * 30)
                
                # Show a snippet of the summary
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_content = f.read()
                    
                # Extract key stats
                lines = summary_content.split('\n')
                for line in lines:
                    if 'Total Speaker Segments:' in line or 'Named Speakers Identified:' in line:
                        print(f"  {line.strip()}")
                
                print(f"\n💡 TIP: Open '{base_filename}_speakers.txt' for the cleanest reading experience!")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled by user.")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False


def main():
    """Main entry point"""
    downloader = CaptionDownloaderWithSpeakers()
    
    while True:
        success = downloader.run()
        
        if success:
            print("\n" + "=" * 50)
            another = input("Process another video? (y/n): ").lower().strip()
            if another not in ['y', 'yes']:
                break
        else:
            print("\n" + "=" * 50)
            retry = input("Try again? (y/n): ").lower().strip()
            if retry not in ['y', 'yes']:
                break
        
        print("\n")  # Extra spacing
    
    print("\n👋 Thank you for using the Caption Downloader!")


if __name__ == "__main__":
    main()