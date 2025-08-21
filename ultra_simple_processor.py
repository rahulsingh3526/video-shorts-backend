"""
Ultra-Simple Video Processor for Debugging

This is the most basic version possible to identify what's failing.
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path


def create_ultra_simple_video(input_path: str, output_path: str) -> bool:
    """
    Create the most basic split-screen video possible.
    
    Args:
        input_path: Input video file
        output_path: Output video file
        
    Returns:
        bool: Success status
    """
    try:
        print(f"🎬 Ultra-simple processing: {input_path} -> {output_path}")
        
        # Just resize the input video to vertical format - no split screen
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black',
            '-c:v', 'libx264', '-preset', 'superfast', '-crf', '30',
            '-t', '30',  # Max 30 seconds
            '-an', '-y', output_path
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ Ultra-simple processing successful")
            return True
        else:
            print(f"❌ FFmpeg failed:")
            print(f"Return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ultra-simple processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False