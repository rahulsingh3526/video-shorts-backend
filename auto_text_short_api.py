#!/usr/bin/env python3
"""
Auto Text-to-Video Short Creator - API Version

Processes text input and creates a short video.
Simplified version that works with the existing backend structure.

Usage:
    python auto_text_short_api.py <text_content>
"""

import os
import sys
import json
import random
import tempfile
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


def create_text_to_video(text_content: str) -> str:
    """
    Create a video from text content.
    
    Args:
        text_content: The text content to convert to video
        
    Returns:
        str: Path to the output video
        
    Raises:
        Exception: If processing fails
    """
    print_step(f"📝 Creating video from text ({len(text_content)} characters)")
    
    # Create output directory
    output_dir = Path("results/creator_shorts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"text_short_{timestamp}.mp4"
    output_path = output_dir / output_filename
    
    print_substep(f"🎯 Output will be: {output_path}")
    
    try:
        # Create a simple text-to-video using ffmpeg
        # This creates a basic video with text overlay on a colored background
        print_step("🎬 Creating text video...")
        
        # Create a temporary text file for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(text_content)
            text_file_path = tmp_file.name
        
        try:
            # Create a 60-second video with text overlay
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'color=c=black:s=1080x1920:d=60',  # Black background, full HD vertical, 60 seconds
                '-vf', f"drawtext=textfile='{text_file_path}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,60)'",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-r', '30',
                str(output_path),
                '-y'  # Overwrite output file
            ]
            
            print_substep(f"🛠️ Running: ffmpeg with text overlay")
            
            result = subprocess.run(cmd, capture_output=True, text=True)  # No timeout - let it take the time it needs
            
            if result.returncode != 0:
                # Try alternative approach without system fonts
                print_substep("⚠️ Trying alternative text rendering...")
                cmd = [
                    'ffmpeg',
                    '-f', 'lavfi',
                    '-i', f'color=c=black:s=1080x1920:d=60,drawtext=text=\'{text_content[:200]}...\':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-r', '30',
                    str(output_path),
                    '-y'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)  # No timeout - let it take the time it needs
                
                if result.returncode != 0:
                    error_msg = result.stderr or "FFmpeg text processing failed"
                    raise Exception(f"Text video processing failed: {error_msg}")
        
        finally:
            # Clean up temporary text file
            try:
                os.unlink(text_file_path)
            except:
                pass
        
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            print_step("✅ Text video created successfully!")
            print_substep(f"📁 Output: {output_path}")
            print_substep(f"📊 File size: {file_size:.1f} MB")
            return str(output_path)
        else:
            raise Exception("Text video processing completed but output file not found")
            
    except Exception as e:
        print_step(f"❌ Error creating text video: {e}")
        raise


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description='Create short video from text')
    parser.add_argument('text_content', help='Text content to convert to video')
    
    args = parser.parse_args()
    
    try:
        output_path = create_text_to_video(args.text_content)
        print_step(f"✅ Success! Text video saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print_step(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()