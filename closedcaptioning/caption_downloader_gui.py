#!/usr/bin/env python3
"""
Legislative Caption Downloader - GUI Version
Downloads closed captions from New Mexico Legislature Harmony/Sliq.net streaming system.
Uses popup dialogs for user input.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import os
import sys
from caption_downloader import CaptionDownloader


class CaptionDownloaderGUI:
    def __init__(self):
        # Create a hidden root window
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window
        
        # Center dialogs on screen
        self.root.eval('tk::PlaceWindow . center')
        
        self.downloader = CaptionDownloader()
        
    def get_url_input(self):
        """Get URL from user via dialog"""
        url = simpledialog.askstring(
            "Caption Downloader",
            "Enter the New Mexico Legislature video URL:",
            initialvalue="https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/"
        )
        return url
    
    def get_format_selection(self):
        """Get format selection from user via checkboxes"""
        format_window = tk.Toplevel(self.root)
        format_window.title("Select Output Formats")
        format_window.geometry("400x300")
        format_window.transient(self.root)
        format_window.grab_set()
        
        # Center the window
        format_window.update_idletasks()
        x = (format_window.winfo_screenwidth() // 2) - (format_window.winfo_width() // 2)
        y = (format_window.winfo_screenheight() // 2) - (format_window.winfo_height() // 2)
        format_window.geometry(f"+{x}+{y}")
        
        # Instructions
        tk.Label(format_window, 
                text="Select the output formats you want:", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Format options with descriptions
        formats = {
            'txt': 'Plain text transcript (easy to read)',
            'vtt': 'WebVTT format (for web video players)',
            'srt': 'SubRip format (for video editing software)',
            'csv': 'CSV with timestamps (for data analysis)',
            'json': 'JSON format (raw data with metadata)'
        }
        
        # Variables to store checkbox states
        format_vars = {}
        
        # Create checkboxes
        for fmt, description in formats.items():
            var = tk.BooleanVar()
            if fmt == 'txt':  # Default to text format
                var.set(True)
            format_vars[fmt] = var
            
            frame = tk.Frame(format_window)
            frame.pack(anchor='w', padx=20, pady=5)
            
            checkbox = tk.Checkbutton(frame, 
                                    text=fmt.upper(), 
                                    variable=var,
                                    font=("Arial", 10, "bold"))
            checkbox.pack(side='left')
            
            label = tk.Label(frame, text=f"- {description}", font=("Arial", 9))
            label.pack(side='left', padx=(10, 0))
        
        # Result variable
        selected_formats = []
        
        def on_ok():
            nonlocal selected_formats
            selected_formats = [fmt for fmt, var in format_vars.items() if var.get()]
            if not selected_formats:
                messagebox.showwarning("No Selection", "Please select at least one format.")
                return
            format_window.destroy()
        
        def on_cancel():
            nonlocal selected_formats
            selected_formats = None
            format_window.destroy()
        
        # Buttons
        button_frame = tk.Frame(format_window)
        button_frame.pack(pady=20)
        
        ok_button = tk.Button(button_frame, text="Download", command=on_ok, 
                             bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                             padx=20, pady=5)
        ok_button.pack(side='left', padx=10)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel,
                                 bg="#f44336", fg="white", font=("Arial", 10, "bold"),
                                 padx=20, pady=5)
        cancel_button.pack(side='left', padx=10)
        
        # Wait for user input
        format_window.wait_window()
        
        return selected_formats
    
    def get_output_directory(self):
        """Get output directory from user"""
        directory = filedialog.askdirectory(
            title="Select output directory",
            initialdir=os.getcwd()
        )
        return directory if directory else os.getcwd()
    
    def show_progress_dialog(self, url):
        """Show a progress dialog while downloading"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading Captions")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (progress_window.winfo_width() // 2)
        y = (progress_window.winfo_screenheight() // 2) - (progress_window.winfo_height() // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        # Progress message
        tk.Label(progress_window, 
                text="Downloading captions...", 
                font=("Arial", 12)).pack(pady=20)
        
        tk.Label(progress_window, 
                text="Please wait while we fetch and process the video captions.",
                font=("Arial", 9)).pack(pady=5)
        
        # URL display (truncated if too long)
        url_display = url if len(url) < 60 else url[:57] + "..."
        tk.Label(progress_window, 
                text=f"URL: {url_display}",
                font=("Arial", 8),
                fg="gray").pack(pady=5)
        
        # Update the window
        progress_window.update()
        
        return progress_window
    
    def run(self):
        """Main GUI flow"""
        try:
            # Welcome message
            messagebox.showinfo(
                "Caption Downloader", 
                "Welcome to the New Mexico Legislature Caption Downloader!\n\n"
                "This tool will help you download closed captions from legislative videos."
            )
            
            # Get URL
            url = self.get_url_input()
            if not url:
                messagebox.showinfo("Cancelled", "Operation cancelled by user.")
                return
            
            # Validate URL
            if "harmony.sliq.net" not in url.lower():
                result = messagebox.askyesno(
                    "URL Warning", 
                    "This doesn't appear to be a New Mexico Legislature URL.\n\n"
                    "Do you want to continue anyway?"
                )
                if not result:
                    return
            
            # Get formats
            formats = self.get_format_selection()
            if formats is None:
                messagebox.showinfo("Cancelled", "Operation cancelled by user.")
                return
            
            # Get output directory
            output_dir = self.get_output_directory()
            
            # Show progress dialog
            progress_window = self.show_progress_dialog(url)
            
            try:
                # Download captions
                success = self.downloader.download_captions(url, formats, output_dir)
                
                # Close progress dialog
                progress_window.destroy()
                
                if success:
                    # Success message
                    format_list = ", ".join([f.upper() for f in formats])
                    messagebox.showinfo(
                        "Download Complete!", 
                        f"Captions successfully downloaded in {format_list} format(s)!\n\n"
                        f"Files saved to: {output_dir}\n\n"
                        "You can now use these caption files with video players, "
                        "editing software, or for transcript analysis."
                    )
                    
                    # Ask if user wants to open the folder
                    if messagebox.askyesno("Open Folder", "Would you like to open the output folder?"):
                        if sys.platform == "darwin":  # macOS
                            os.system(f'open "{output_dir}"')
                        elif sys.platform == "win32":  # Windows
                            os.system(f'explorer "{output_dir}"')
                        else:  # Linux
                            os.system(f'xdg-open "{output_dir}"')
                else:
                    messagebox.showerror(
                        "Download Failed", 
                        "Failed to download captions. This could be because:\n\n"
                        "• The URL is invalid or inaccessible\n"
                        "• The video doesn't have captions\n"
                        "• Network connection issues\n\n"
                        "Please check the URL and try again."
                    )
                    
            except Exception as e:
                # Close progress dialog if still open
                try:
                    progress_window.destroy()
                except:
                    pass
                
                messagebox.showerror(
                    "Error", 
                    f"An error occurred during download:\n\n{str(e)}\n\n"
                    "Please try again or check your internet connection."
                )
        
        except Exception as e:
            messagebox.showerror(
                "Unexpected Error", 
                f"An unexpected error occurred:\n\n{str(e)}"
            )
        
        finally:
            # Ask if user wants to download another
            if messagebox.askyesno("Continue?", "Would you like to download captions from another video?"):
                self.run()  # Restart the process
            else:
                messagebox.showinfo("Thank You", "Thank you for using the Caption Downloader!")


def main():
    """Main entry point for GUI version"""
    try:
        app = CaptionDownloaderGUI()
        app.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()