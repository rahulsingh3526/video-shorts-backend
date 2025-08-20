#!/usr/bin/env python3
"""
Auto Text-to-Video Short Creator - API Version

Processes text from a specified file and creates a short video.
Modified for API usage with direct file path input.

Usage:
    python auto_text_short_api.py <text_file_path>
"""

import sys
import random
from pathlib import Path
from datetime import datetime
import argparse

from utils.console import print_step, print_substep
from create_text_short import main as create_text_short_main
from video_creation.background import load_background_options


def get_random_background():
    """
    Select a random background from available options.
    
    Returns:
        str: Background name to use
    """
    try:
        background_options = load_background_options()
        available_backgrounds = list(background_options.keys())
        
        # Remove comment key if it exists
        if "__comment" in available_backgrounds:
            available_backgrounds.remove("__comment")
        
        if not available_backgrounds:
            print_substep("⚠️ No background options found, using minecraft-2 as fallback")
            return "minecraft-2"
        
        print_substep(f"📋 Available backgrounds: {', '.join(available_backgrounds)}")
        
        # Select random background
        selected = random.choice(available_backgrounds)
        return selected
    
    except Exception as e:
        print_substep(f"⚠️ Could not load backgrounds: {e}, using minecraft-2")
        return "minecraft-2"


def read_text_file(text_path: str) -> str:
    """
    Read text content from the specified file.
    
    Args:
        text_path: Path to the text file
        
    Returns:
        Text content from the file
        
    Raises:
        FileNotFoundError: If file is not found or empty
    """
    text_file = Path(text_path)
    
    if not text_file.exists():
        raise FileNotFoundError(f"Text file not found: {text_path}")
    
    if not text_file.is_file():
        raise ValueError(f"Path is not a file: {text_path}")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        raise FileNotFoundError(f"Text file is empty: {text_path}")
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    print_substep(f"Found story with {len(lines)} lines")
    print_substep(f"Title: {lines[0][:50]}{'...' if len(lines[0]) > 50 else ''}")
    
    word_count = len(content.split())
    print_substep(f"Word count: {word_count}")
    
    return content


def process_text_file(text_path: str):
    """
    Process a text file and create a short video.
    
    Args:
        text_path: Path to the text file to process
        
    Returns:
        str: Path to the created video file
    """
    print_step("🚀 Auto Text-to-Video Short Creator - API Mode")
    
    try:
        # Read the text content
        print_substep("📖 Reading text content...")
        text_content = read_text_file(text_path)
        
        # Select random background for variety
        random_background = get_random_background()
        print_substep(f"🎮 Random background selected: {random_background}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a short title from the first few words for filename
        first_words = ' '.join(text_content.split()[:5])
        # Clean up filename-unsafe characters
        safe_title = ''.join(c for c in first_words if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:20]  # Limit length
        
        output_name = f"auto_text_{safe_title}_{timestamp}.mp4"
        
        # Ensure output directory exists
        output_dir = Path("results") / "custom"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_name
        
        print_substep(f"🎯 Output will be: {output_path}")
        
        # Prepare arguments for create_text_short.py
        original_argv = sys.argv.copy()
        
        # Check if default background music exists
        default_music = Path("assets/backgrounds/audio/Super Lofi World-lofi.mp3")
        
        sys.argv = [
            "create_text_short.py",
            str(text_path),
            "--transcription-method", "whisper",
            "--output", str(output_path),
            "--background", random_background,
            "--fps", "30",  # Force 30 FPS for social media compatibility
            "--tts", "gtts"  # Use Google TTS for reliability
        ]
        
        # Add background music if available
        if default_music.exists():
            sys.argv.extend(["--background-music", str(default_music)])
            sys.argv.extend(["--music-volume", "0.2"])  # Slightly louder for text videos
        else:
            print_substep("⚠️ Background music not found, proceeding without music")
        
        print_substep(f"🛠️ Running create_text_short with: {' '.join(sys.argv[1:])}")
        
        # Run the main create_text_short function
        result_path = create_text_short_main()
        
        # Restore original argv
        sys.argv = original_argv
        
        if result_path and Path(result_path).exists():
            print_step(f"✅ Text-to-video short created successfully!")
            print_substep(f"📁 Output: {result_path}")
            print_substep(f"📊 File size: {Path(result_path).stat().st_size / (1024 * 1024):.1f} MB")
            return str(result_path)
        else:
            raise Exception("Video processing completed but output file not found")
            
    except Exception as e:
        # Restore original argv in case of error
        sys.argv = original_argv
        print_step(f"❌ Error creating text-to-video short: {e}")
        raise


def main():
    """
    Main function for API usage.
    """
    if len(sys.argv) != 2:
        print("Usage: python auto_text_short_api.py <text_file_path>")
        sys.exit(1)
    
    text_path = sys.argv[1]
    
    try:
        result = process_text_file(text_path)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()