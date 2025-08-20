#!/usr/bin/env python3
"""
Auto Short Video Creator - API Version

Processes a specified video file and creates a short video.
Modified for API usage with direct file path input.

Usage:
    python auto_short_api.py <video_file_path>
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


def get_random_background():
    """
    Select a random background from available downloaded videos.
    
    Returns:
        str: Background name to use
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
            print_substep("⚠️ No downloaded background videos found, using minecraft-2 as fallback")
            return "minecraft-2"
        
        print_substep(f"📋 Available backgrounds: {', '.join(available_backgrounds)}")
        
        # Select random background from downloaded ones
        selected = random.choice(available_backgrounds)
        return selected
    
    except Exception as e:
        print_substep(f"⚠️ Could not load backgrounds: {e}, using minecraft-2")
        return "minecraft-2"


def process_video_file(video_path: str):
    """
    Process a specific video file and create a short video.
    
    Args:
        video_path: Path to the video file to process
    """
    print_step("🚀 Auto Short Video Creator - API Mode")
    
    video_file = Path(video_path)
    
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not video_file.is_file():
        raise ValueError(f"Path is not a file: {video_path}")
    
    # Check if it's a video file
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    if video_file.suffix.lower() not in video_extensions:
        raise ValueError(f"Unsupported video format: {video_file.suffix}")
    
    try:
        # Select random background for variety
        random_background = get_random_background()
        print_substep(f"🎮 Random background selected: {random_background}")
        
        # Show video info
        file_size = video_file.stat().st_size / (1024 * 1024)  # MB
        mod_time = datetime.fromtimestamp(video_file.stat().st_mtime)
        
        print_substep(f"📹 Video: {video_file.name}")
        print_substep(f"📁 Size: {file_size:.1f} MB")
        print_substep(f"🕐 Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"auto_short_{timestamp}.mp4"
        
        # Ensure output directory exists
        output_dir = Path("results") / "creator_shorts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_name
        
        print_substep(f"🎯 Output will be: {output_path}")
        
        # Prepare arguments for create_short.py
        # We'll modify sys.argv to simulate command line arguments
        original_argv = sys.argv.copy()
        
        # Check if default background music exists
        default_music = Path("assets/backgrounds/audio/Super Lofi World-lofi.mp3")
        
        sys.argv = [
            "create_short.py",
            str(video_file),
            "--transcription-method", "whisper",
            "--output", str(output_path),
            "--background", random_background,  # Random background type
            "--no-bright-analysis",  # Use random clips for variety
            "--fps", "30"  # Force 30 FPS for social media compatibility
        ]
        
        # Add background music if available
        if default_music.exists():
            sys.argv.extend(["--background-music", str(default_music)])
            sys.argv.extend(["--music-volume", "0.15"])  # Quiet background music
        else:
            print_substep("⚠️ Background music not found, proceeding without music")
        
        print_substep(f"🛠️ Running create_short with: {' '.join(sys.argv[1:])}")
        
        # Run the main create_short function
        result_path = create_short_main()
        
        # Restore original argv
        sys.argv = original_argv
        
        if result_path and Path(result_path).exists():
            print_step(f"✅ Short video created successfully!")
            print_substep(f"📁 Output: {result_path}")
            print_substep(f"📊 File size: {Path(result_path).stat().st_size / (1024 * 1024):.1f} MB")
            return str(result_path)
        else:
            raise Exception("Video processing completed but output file not found")
            
    except Exception as e:
        # Restore original argv in case of error
        sys.argv = original_argv
        print_step(f"❌ Error creating short video: {e}")
        raise


def main():
    """
    Main function for API usage.
    """
    if len(sys.argv) != 2:
        print("Usage: python auto_short_api.py <video_file_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    try:
        result = process_video_file(video_path)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()