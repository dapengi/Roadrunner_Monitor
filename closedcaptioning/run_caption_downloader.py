#!/usr/bin/env python3
"""
Simple launcher for the Caption Downloader
Double-click this file to run the interactive caption downloader.
"""

import os
import sys

def main():
    """Launch the interactive caption downloader"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    interactive_script = os.path.join(script_dir, "caption_downloader_interactive.py")
    
    if os.path.exists(interactive_script):
        os.system(f'python "{interactive_script}"')
    else:
        print("Error: caption_downloader_interactive.py not found!")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()