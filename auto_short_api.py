#!/usr/bin/env python3
"""
Auto Short Video Creator - API Version

Processes a specified video file and creates a short video.
Simplified version that works with the existing backend structure.

Usage:
    python auto_short_api.py <video_file_path>
"""

import os
import sys
import gc
import json
import random
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import subprocess

from utils.console import print_step, print_substep


def get_random_background():
    """
    Select a random background from available options.
    
    Returns:
        str: Background name to use
    """
    backgrounds = ['minecraft', 'rocket_league', 'fall_guys', 'parkour', 'subway_surfers']
    return random.choice(backgrounds)


def process_video_to_short(input_video_path: str) -> str:
    """
    Process a video file and create a short video.
    
    Args:
        input_video_path: Path to the input video file
        
    Returns:
        str: Path to the output short video
        
    Raises:
        Exception: If processing fails
    """
    input_path = Path(input_video_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_video_path}")
    
    print_step(f"🎥 Processing video: {input_path.name}")
    print_substep(f"📁 Input: {input_path}")
    
    # Create output directory
    output_dir = Path("results/creator_shorts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"short_{timestamp}.mp4"
    output_path = output_dir / output_filename
    
    print_substep(f"🎯 Output will be: {output_path}")
    
    try:
        # Simple video processing using ffmpeg
        # This creates a basic short video by extracting a segment
        print_step("🎬 Creating short video...")
        
        # Simple landscape to vertical conversion - core functionality only
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-ss', '10',   # Start at 10 seconds
            '-t', '30',    # 30-second duration
            '-vf', 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280',  # Convert to vertical
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'ultrafast',  # Fast processing
            '-threads', '1',    # Single thread for memory
            str(output_path),
            '-y'
        ]
        
        print_substep(f"🛠️ Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)  # No timeout - let it take the time it needs
        
        # Force garbage collection after processing
        gc.collect()
        
        if result.returncode != 0:
            error_msg = result.stderr or "FFmpeg processing failed"
            raise Exception(f"Video processing failed: {error_msg}")
        
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            print_step("✅ Short video created successfully!")
            print_substep(f"📁 Output: {output_path}")
            print_substep(f"📊 File size: {file_size:.1f} MB")
            return str(output_path)
        else:
            raise Exception("Video processing completed but output file not found")
            
    except Exception as e:
        print_step(f"❌ Error creating short video: {e}")
        raise


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description='Create short video from input video')
    parser.add_argument('input_video', help='Path to input video file')
    
    args = parser.parse_args()
    
    try:
        output_path = process_video_to_short(args.input_video)
        print_step(f"✅ Success! Short video saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print_step(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()