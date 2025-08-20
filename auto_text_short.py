#!/usr/bin/env python3
"""
Auto Text-to-Video Short Creator

Automatically processes text from input/story.txt and creates a short video.
Just update the story.txt file and run this script!

Usage:
    python auto_text_short.py
"""

import sys
import random
from pathlib import Path
from datetime import datetime
import argparse

from utils.console import print_step, print_substep
from create_text_short import main as create_text_short_main
from video_creation.background import load_background_options


def find_story_text(input_dir: Path) -> str:
    """
    Read text content from the story.txt file.
    
    Args:
        input_dir: Path to the input directory
        
    Returns:
        Text content from the story file
        
    Raises:
        FileNotFoundError: If story.txt is not found or empty
    """
    story_file = input_dir / "story.txt"
    
    if not story_file.exists():
        raise FileNotFoundError(f"Story file not found: {story_file}")
    
    with open(story_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        raise FileNotFoundError(f"Story file is empty: {story_file}")
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    print_substep(f"Found story with {len(lines)} lines")
    print_substep(f"Title: {lines[0][:50]}{'...' if len(lines[0]) > 50 else ''}")
    
    return content


def get_random_backgrounds() -> tuple:
    """
    Select random background video and audio from available options.
    
    Returns:
        Tuple of (video_background, audio_background)
    """
    try:
        background_options = load_background_options()
        
        # Get available backgrounds
        video_backgrounds = list(background_options["video"].keys())
        audio_backgrounds = list(background_options["audio"].keys())
        
        # Select random backgrounds
        selected_video = random.choice(video_backgrounds)
        selected_audio = random.choice(audio_backgrounds)
        
        print_substep(f"🎮 Random video background: {selected_video}")
        print_substep(f"🎵 Random audio background: {selected_audio}")
        
        return selected_video, selected_audio
        
    except Exception as e:
        print_substep(f"⚠️ Could not load backgrounds: {e}, using defaults")
        return "minecraft", "lofi"


def auto_create_text_short():
    """
    Automatically create a short video from story.txt.
    """
    print_step("🚀 Auto Text-to-Video Creator")
    
    # Define paths
    input_dir = Path("input")
    
    try:
        # Read story content
        print_substep("📖 Reading story content...")
        story_content = find_story_text(input_dir)
        
        # Get random backgrounds for variety
        video_bg, audio_bg = get_random_backgrounds()
        
        # Show content info
        word_count = len(story_content.split())
        line_count = len([line for line in story_content.split('\n') if line.strip()])
        
        print_substep(f"📝 Content: {word_count} words, {line_count} lines")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create safe title for filename
        lines = [line.strip() for line in story_content.split('\n') if line.strip()]
        title = lines[0] if lines else "story"
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
        safe_title = safe_title.replace(' ', '_')
        
        output_name = f"auto_text_{safe_title}_{timestamp}.mp4"
        output_path = Path("results") / "custom" / output_name
        
        print_substep(f"🎯 Output will be: {output_path}")
        
        # Prepare arguments for create_text_short.py
        original_argv = sys.argv.copy()
        
        sys.argv = [
            "create_text_short.py",
            "--file", "input/story.txt",
            "--output", str(output_path),
            "--background-video", video_bg,
            "--background-audio", audio_bg,
            "--fps", "30"  # Force 30 FPS for social media compatibility
        ]
        
        print_step("🎬 Starting video processing...")
        
        # Call the main function from create_text_short.py
        try:
            create_text_short_main()
            print_step("✅ Auto text-to-video creation completed!")
            print_substep(f"📱 Your video is ready: {output_path}", style="bold green")
            return str(output_path)
            
        except Exception as e:
            print_substep(f"❌ Error during video creation: {str(e)}", style="bold red")
            raise
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
            
    except FileNotFoundError as e:
        print_substep(f"❌ {str(e)}", style="bold red")
        print_substep("💡 Add text content to input/story.txt and try again", style="yellow")
        print_substep("📝 Format: First line = title, remaining lines = content", style="yellow")
        sys.exit(1)
    except Exception as e:
        print_substep(f"❌ Unexpected error: {str(e)}", style="bold red")
        sys.exit(1)


def main():
    """Main entry point with command line argument support."""
    parser = argparse.ArgumentParser(
        description="Automatically create text-to-video shorts from input/story.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python auto_text_short.py                    # Process story.txt with random backgrounds
    
Workflow:
    1. Add your text content to input/story.txt
    2. Run: python auto_text_short.py  
    3. Find your video in results/custom/
    
Text Format:
    - First line becomes the video title
    - Remaining lines become the video content
    - Each line will be spoken separately
        """
    )
    
    parser.add_argument(
        "--preview",
        action="store_true", 
        help="Preview the story content without creating video"
    )
    
    args = parser.parse_args()
    
    if args.preview:
        # Preview the story content
        input_dir = Path("input")
        try:
            story_content = find_story_text(input_dir)
            lines = [line.strip() for line in story_content.split('\n') if line.strip()]
            
            print_step("📖 Story Preview")
            print_substep(f"Title: {lines[0]}")
            print_substep(f"Content lines: {len(lines) - 1}")
            print()
            
            for i, line in enumerate(lines):
                if i == 0:
                    print(f"📝 Title: {line}")
                else:
                    print(f"📄 Line {i}: {line}")
            
            word_count = len(story_content.split())
            estimated_duration = max(10, word_count * 0.4)  # ~150 words per minute
            print()
            print_substep(f"Estimated video duration: {estimated_duration:.1f} seconds")
            
        except Exception as e:
            print_substep(f"Error reading story: {e}", style="bold red")
        
        return
    
    # Run auto creation
    auto_create_text_short()


if __name__ == "__main__":
    main()