#!/usr/bin/env python3
"""
Auto Short Video Creator - API Version

Processes a specified video file and creates a short video.
Modified for API usage with direct file path input.

Usage:
    python auto_short.py <video_file_path>
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
import argparse

from utils.console import print_step, print_substep
from create_short import main as create_short_main


def find_latest_video(input_dir: Path) -> Path:
    """
    Find the most recently added video file in the input directory.
    
    Args:
        input_dir: Path to the input directory
        
    Returns:
        Path to the latest video file
        
    Raises:
        FileNotFoundError: If no video files are found
    """
    # Common video file extensions
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Find all video files
    video_files = []
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            # Get modification time
            mod_time = file_path.stat().st_mtime
            video_files.append((file_path, mod_time))
    
    if not video_files:
        raise FileNotFoundError(f"No video files found in {input_dir}")
    
    # Sort by modification time (newest first)
    video_files.sort(key=lambda x: x[1], reverse=True)
    latest_video = video_files[0][0]
    
    print_substep(f"Found {len(video_files)} video(s) in input folder")
    print_substep(f"Latest video: {latest_video.name}", style="bold green")
    
    return latest_video


def get_random_background() -> str:
    """
    Select a random background type from EXISTING downloaded videos only.
    
    Returns:
        Random background type name from available downloads
    """
    try:
        backgrounds_file = Path("utils") / "background_videos.json"
        video_dir = Path("assets") / "backgrounds" / "video"
        
        with open(backgrounds_file, 'r') as f:
            background_options = json.load(f)
        
        # Find which backgrounds are actually downloaded (complete .mp4 files)
        available_backgrounds = []
        
        for bg_name, bg_config in background_options.items():
            if bg_name == "__comment":
                continue
                
            # Construct expected filename
            filename = f"{bg_config[2]}-{bg_config[1]}"
            video_path = video_dir / filename
            
            # Check if the video file exists and is complete (not a .part file)
            if video_path.exists() and video_path.suffix == '.mp4':
                available_backgrounds.append(bg_name)
                print_substep(f"✅ Found: {bg_name} ({filename})")
        
        if not available_backgrounds:
            print_substep("⚠️ No downloaded background videos found, using minecraft as fallback")
            return "minecraft"
        
        print_substep(f"📋 Available backgrounds: {', '.join(available_backgrounds)}")
        
        # Select random background from downloaded ones
        selected = random.choice(available_backgrounds)
        return selected
    
    except Exception as e:
        print_substep(f"⚠️ Could not load backgrounds: {e}, using minecraft")
        return "minecraft"


def auto_create_short():
    """
    Automatically create a short video from the latest video in input folder.
    """
    print_step("🚀 Auto Short Video Creator")
    
    # Define paths
    input_dir = Path("input")
    
    try:
        # Find the latest video
        print_substep("🔍 Looking for videos in input folder...")
        latest_video = find_latest_video(input_dir)
        
        # Select random background for variety
        random_background = get_random_background()
        print_substep(f"🎮 Random background selected: {random_background}")
        
        # Show video info
        file_size = latest_video.stat().st_size / (1024 * 1024)  # MB
        mod_time = datetime.fromtimestamp(latest_video.stat().st_mtime)
        
        print_substep(f"📹 Video: {latest_video.name}")
        print_substep(f"📁 Size: {file_size:.1f} MB")
        print_substep(f"🕐 Added: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"auto_short_{timestamp}.mp4"
        output_path = Path("results") / "creator_shorts" / output_name
        
        print_substep(f"🎯 Output will be: {output_path}")
        
        # Prepare arguments for create_short.py
        # We'll modify sys.argv to simulate command line arguments
        original_argv = sys.argv.copy()
        
        # Check if default background music exists
        default_music = Path("assets/backgrounds/audio/Super Lofi World-lofi.mp3")
        
        sys.argv = [
            "create_short.py",
            str(latest_video),
            "--transcription-method", "whisper",
            "--output", str(output_path),
            "--background", random_background,  # Random background type
            "--no-bright-analysis",  # Use random clips for variety
            "--fps", "30"  # Force 30 FPS for social media compatibility
        ]
        
        # Add background music if available
        if default_music.exists():
            sys.argv.extend(["--background-music", str(default_music)])
            print_substep(f"🎵 Adding background music: {default_music.name}")
        else:
            print_substep("⚠️ Default background music not found, continuing without music")
        
        print_step("🎬 Starting video processing...")
        
        # Call the main function from create_short.py
        try:
            create_short_main()
            print_step("✅ Auto short creation completed!")
            print_substep(f"📱 Your short video is ready: {output_path}", style="bold green")
            return str(output_path)
            
        except Exception as e:
            print_substep(f"❌ Error during video creation: {str(e)}", style="bold red")
            raise
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
            
    except FileNotFoundError as e:
        print_substep(f"❌ {str(e)}", style="bold red")
        print_substep("💡 Add a video file to the input/ folder and try again", style="yellow")
        sys.exit(1)
    except Exception as e:
        print_substep(f"❌ Unexpected error: {str(e)}", style="bold red")
        sys.exit(1)


def main():
    """Main entry point with command line argument support."""
    parser = argparse.ArgumentParser(
        description="Automatically create short videos from the latest video in input folder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python auto_short.py                    # Process latest video with defaults
    
Workflow:
    1. Drop your landscape video into the input/ folder
    2. Run: python auto_short.py
    3. Find your short video in results/creator_shorts/
        """
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all videos in input folder"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List all videos in input folder
        input_dir = Path("input")
        try:
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            video_files = []
            
            for file_path in input_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    video_files.append((file_path, mod_time, size_mb))
            
            if not video_files:
                print("No video files found in input folder.")
                return
            
            # Sort by modification time (newest first)
            video_files.sort(key=lambda x: x[1], reverse=True)
            
            print(f"Found {len(video_files)} video(s) in input folder:")
            print()
            for i, (video_path, mod_time, size_mb) in enumerate(video_files):
                status = "📍 LATEST" if i == 0 else "   "
                print(f"{status} {video_path.name}")
                print(f"      📁 {size_mb:.1f} MB  🕐 {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            
        except Exception as e:
            print(f"Error listing videos: {e}")
        
        return
    
    # Run auto creation
    auto_create_short()


if __name__ == "__main__":
    main()