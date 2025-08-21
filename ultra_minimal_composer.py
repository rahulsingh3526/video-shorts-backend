"""
Ultra-Minimal Video Composer for 512MB Memory Limit

This version removes all heavy dependencies and uses only basic FFmpeg
to create a simple split-screen video without transcription.
Designed to work within Render's strict 512MB memory limit.
"""

import os
import gc
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import uuid
import shutil

class UltraMinimalComposer:
    """Ultra-minimal video composer for extreme memory constraints."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize with temporary directory for processing."""
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(exist_ok=True)
        
    def create_split_screen_video(self, input_video_path: str, output_path: str) -> bool:
        """
        Create split-screen video with minimal memory usage.
        
        Args:
            input_video_path: Path to input landscape video
            output_path: Path for output short video
            
        Returns:
            bool: Success status
        """
        try:
            print("🎬 Starting ultra-minimal video processing...")
            
            # Step 1: Get video duration using FFprobe (very lightweight)
            duration = self._get_video_duration(input_video_path)
            print(f"📹 Video duration: {duration:.2f}s")
            
            # Step 2: Create top video (user's video, resized)
            top_video_path = self._create_top_video(input_video_path)
            print("📱 Top video section created")
            
            # Step 3: Create bottom video (simple green background with text)
            bottom_video_path = self._create_bottom_video(duration)
            print("🎮 Bottom video section created")
            
            # Step 4: Combine videos vertically
            self._combine_videos_vertically(top_video_path, bottom_video_path, output_path)
            print("✅ Split-screen video created successfully!")
            
            # Cleanup
            self._cleanup_temp_files()
            
            return True
            
        except Exception as e:
            print(f"❌ Error in video processing: {str(e)}")
            self._cleanup_temp_files()
            return False
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFprobe (lightweight)."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"Warning: Could not get duration: {e}")
            return 30.0  # Default fallback
    
    def _create_top_video(self, input_path: str) -> str:
        """Create top half video (user's video, resized to 1080x640)."""
        top_video_path = self.temp_dir / f"top_{uuid.uuid4().hex[:8]}.mp4"
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'scale=1080:640:force_original_aspect_ratio=decrease,pad=1080:640:(ow-iw)/2:(oh-ih)/2:black',
            '-c:v', 'libx264', '-preset', 'ultrafast',  # Fastest encoding
            '-crf', '30',  # Lower quality for speed
            '-an',  # No audio
            '-y', str(top_video_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return str(top_video_path)
    
    def _create_bottom_video(self, duration: float) -> str:
        """Create bottom half with simple background and text."""
        bottom_video_path = self.temp_dir / f"bottom_{uuid.uuid4().hex[:8]}.mp4"
        
        # Create simple green background with static text
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'color=c=darkgreen:s=1080x640:d={duration}',
            '-vf', 'drawtext=text=Gameplay Background:fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '30', '-an',
            '-y', str(bottom_video_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return str(bottom_video_path)
    
    def _combine_videos_vertically(self, top_path: str, bottom_path: str, output_path: str):
        """Combine top and bottom videos into final split-screen format."""
        cmd = [
            'ffmpeg',
            '-i', top_path,
            '-i', bottom_path,
            '-filter_complex', '[0:v][1:v]vstack=inputs=2[v]',
            '-map', '[v]',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '28',  # Reasonable quality
            '-an',  # No audio for now
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def _cleanup_temp_files(self):
        """Clean up temporary files to free memory."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            gc.collect()  # Force garbage collection
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


def create_ultra_minimal_short(input_video_path: str, output_video_path: str) -> bool:
    """
    Main function to create ultra-minimal split-screen short video.
    
    Args:
        input_video_path: Path to input landscape video
        output_video_path: Path for output short video
        
    Returns:
        bool: Success status
    """
    composer = UltraMinimalComposer()
    return composer.create_split_screen_video(input_video_path, output_video_path)


# Test function for development
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ultra_minimal_composer.py input_video.mp4 output_video.mp4")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    success = create_ultra_minimal_short(input_path, output_path)
    if success:
        print("✅ Video processing completed successfully!")
    else:
        print("❌ Video processing failed!")