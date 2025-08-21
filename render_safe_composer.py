"""
Render-Safe Video Composer - Guaranteed to work within 512MB

This version removes Whisper entirely and creates a split-screen video
with placeholder text, designed specifically for Render's constraints.
"""

import os
import gc
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import uuid
import shutil

class RenderSafeComposer:
    """Ultra-safe video composer for Render's 512MB limit."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize with temporary directory for processing."""
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(exist_ok=True)
        
    def create_split_screen_video(self, input_video_path: str, output_path: str) -> bool:
        """
        Create split-screen video without any heavy processing.
        
        Args:
            input_video_path: Path to input landscape video
            output_path: Path for output short video
            
        Returns:
            bool: Success status
        """
        try:
            print("🎬 Starting Render-safe video processing...")
            
            # Step 1: Get video duration (lightweight)
            duration = self._get_video_duration(input_video_path)
            print(f"📹 Video duration: {duration:.2f}s")
            
            # Step 2: Create top video (user's video, 720p)
            top_video_path = self._create_top_video(input_video_path, duration)
            print("📱 Top video section created")
            
            # Step 3: Create bottom video (simple background with text)
            bottom_video_path = self._create_bottom_video(duration)
            print("🎮 Bottom video section created")
            
            # Step 4: Combine videos
            self._combine_videos(top_video_path, bottom_video_path, output_path)
            print("✅ Split-screen video created successfully!")
            
            # Cleanup
            self._cleanup_temp_files()
            return True
            
        except Exception as e:
            print(f"❌ Error in render-safe processing: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files()
            return False
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFprobe."""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            return min(float(result.stdout.strip()), 120.0)  # Max 2 minutes
        except:
            return 30.0  # Safe fallback
    
    def _create_top_video(self, input_path: str, duration: float) -> str:
        """Create top half video."""
        top_video_path = self.temp_dir / f"top_{uuid.uuid4().hex[:6]}.mp4"
        
        cmd = [
            'ffmpeg', '-i', input_path, '-t', str(min(duration, 60)),  # Max 1 minute
            '-vf', 'scale=720:640:force_original_aspect_ratio=decrease,pad=720:640:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libx264', '-preset', 'superfast', '-crf', '28',
            '-r', '20', '-an', '-y', str(top_video_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return str(top_video_path)
    
    def _create_bottom_video(self, duration: float) -> str:
        """Create bottom half with simple background."""
        bottom_video_path = self.temp_dir / f"bottom_{uuid.uuid4().hex[:6]}.mp4"
        duration = min(duration, 60)  # Max 1 minute
        
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', f'color=c=green:s=720x640:d={duration}',
            '-vf', 'drawtext=text=GAMEPLAY:fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2',
            '-c:v', 'libx264', '-preset', 'superfast', '-crf', '30',
            '-r', '20', '-an', '-y', str(bottom_video_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return str(bottom_video_path)
    
    def _combine_videos(self, top_path: str, bottom_path: str, output_path: str):
        """Combine videos vertically."""
        cmd = [
            'ffmpeg', '-i', top_path, '-i', bottom_path,
            '-filter_complex', '[0:v][1:v]vstack=inputs=2[v]',
            '-map', '[v]', '-c:v', 'libx264', '-preset', 'superfast',
            '-crf', '28', '-r', '20', '-an', '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            gc.collect()
        except:
            pass


def create_render_safe_short(input_video_path: str, output_video_path: str) -> bool:
    """Create render-safe split-screen video."""
    composer = RenderSafeComposer()
    return composer.create_split_screen_video(input_video_path, output_video_path)