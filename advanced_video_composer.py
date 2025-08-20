"""
Advanced Video Composer for Split-Screen Creator Videos

Creates sophisticated split-screen videos with:
- Top half: User's original landscape video (scaled/cropped)
- Bottom half: Minecraft-style gameplay with transcribed subtitles
- Audio: Original voice boosted + background music mixed
- Subtitles: Word-level timing using Whisper transcription
"""

import random
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import multiprocessing

import ffmpeg
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None

from utils.console import print_step, print_substep
from video_creation.voice_transcriber import extract_voice_from_video, transcribe_audio


class AdvancedVideoComposer:
    """Creates sophisticated split-screen creator videos with gameplay footage."""
    
    def __init__(self, creator_video_path: str):
        """
        Initialize AdvancedVideoComposer.
        
        Args:
            creator_video_path: Path to the creator's landscape video
        """
        self.creator_video_path = Path(creator_video_path)
        self.output_width = 720  # TikTok/Instagram Reels width
        self.output_height = 1280  # TikTok/Instagram Reels height
        self.half_height = self.output_height // 2  # 640 pixels each half
        
        if not self.creator_video_path.exists():
            raise FileNotFoundError(f"Creator video not found: {creator_video_path}")
    
    def create_split_screen_video(self, output_path: Optional[str] = None) -> Path:
        """
        Create a split-screen short video combining creator video and Minecraft footage.
        
        Args:
            output_path: Custom output path, if None will auto-generate
            
        Returns:
            Path to the created short video
        """
        print_step("🎬 Starting advanced split-screen video composition")
        
        # Step 1: Extract and transcribe audio from creator video
        print_step("🎤 Extracting voice from creator video")
        audio_path, video_duration = extract_voice_from_video(str(self.creator_video_path))
        
        print_step("📝 Transcribing voice to text")
        transcription_data = transcribe_audio(audio_path, method="whisper")
        
        # Step 2: Process creator video for top half
        print_step("📹 Processing creator video for top section")
        top_video = self._prepare_creator_video_for_top()
        
        # Step 3: Generate Minecraft footage for bottom half
        print_step("🎮 Generating Minecraft footage for bottom section")
        bottom_video = self._generate_minecraft_footage(video_duration)
        
        # Step 4: Create subtitles for bottom video
        print_step("💬 Creating subtitles from transcription")
        subtitle_path = self._create_subtitles_from_transcription(transcription_data)
        
        # Step 5: Apply subtitles to bottom video
        bottom_video_with_subs = self._apply_subtitles_to_video(bottom_video, subtitle_path)
        
        # Step 6: Combine top and bottom videos
        print_step("🔧 Combining videos into split-screen layout")
        output_path = self._combine_videos(top_video, bottom_video_with_subs, output_path)
        
        print_step("✅ Advanced split-screen video completed!")
        return output_path
    
    def _prepare_creator_video_for_top(self) -> ffmpeg.nodes.FilterNode:
        """
        Prepare the creator video for the top half of the split-screen.
        Scales to fit width with minimal cropping.
        
        Returns:
            FFmpeg filter node for the processed top video
        """
        # Load creator video
        input_video = ffmpeg.input(str(self.creator_video_path))
        
        # Scale to fit width exactly, then crop height to fit half_height
        # This ensures the video fills the entire width with minimal cropping
        top_video = (
            input_video
            .video
            .filter('scale', self.output_width, -1)  # Scale to exact width, maintain aspect ratio
            .filter('scale', self.output_width, self.half_height, force_original_aspect_ratio='increase')  # Scale to fill
            .filter('crop', self.output_width, self.half_height)  # Crop to exact dimensions
        )
        
        return top_video
    
    def _generate_minecraft_footage(self, duration: float) -> str:
        """
        Generate Minecraft background footage for the bottom half.
        
        Args:
            duration: Required duration in seconds
            
        Returns:
            Path to the generated Minecraft footage
        """
        # Use the available Minecraft video
        minecraft_path = Path("assets") / "backgrounds" / "video" / "Itslpsn-minecraft-2.mp4"
        
        if not minecraft_path.exists():
            raise RuntimeError(f"Minecraft background video not found: {minecraft_path}")
        
        # Create temp directory
        temp_dir = Path("assets") / "temp" / "creator_short_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = temp_dir / "minecraft_background.mp4"
        
        if VideoFileClip is None:
            raise RuntimeError("MoviePy not available for video processing")
        
        # Select a random start time for variety
        with VideoFileClip(str(minecraft_path)) as video:
            total_duration = video.duration
            
            # If video is shorter than needed, start from beginning
            if total_duration <= duration:
                start_time = 0
            else:
                # Generate a random start time
                max_start = max(0, total_duration - duration)
                start_time = random.uniform(0, max_start)
            
            print_substep(f"🎲 Using Minecraft clip starting at {start_time:.1f}s")
            
            # Extract the clip
            clip = video.subclip(start_time, start_time + duration)
            clip.write_videofile(str(output_path), codec='libx264', audio=False)
        
        return str(output_path)
    
    def _create_subtitles_from_transcription(self, transcription_data: List[Dict]) -> str:
        """
        Create SRT subtitle file using actual speech timing (3-4 words at a time).
        
        Args:
            transcription_data: List of transcription segments with timestamps and word data
            
        Returns:
            Path to the created SRT file
        """
        temp_dir = Path("assets") / "temp" / "creator_short_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        subtitle_path = temp_dir / "subtitles.srt"
        
        srt_content = []
        subtitle_counter = 1
        
        for segment in transcription_data:
            text = segment['text'].strip()
            if not text:
                continue
            
            # Use word-level timestamps if available (Whisper provides this)
            if 'words' in segment and segment['words']:
                words = segment['words']
                
                # Group words into chunks of 3-4 for better readability
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i+chunk_size]
                    
                    if not chunk_words:
                        continue
                    
                    # Use actual start time of first word and end time of last word
                    chunk_start = chunk_words[0]['start']
                    chunk_end = chunk_words[-1]['end']
                    chunk_text = " ".join([w['word'] for w in chunk_words])
                    
                    start_time = self._format_timestamp(chunk_start)
                    end_time = self._format_timestamp(chunk_end)
                    
                    srt_content.append(
                        f"{subtitle_counter}\n"
                        f"{start_time} --> {end_time}\n"
                        f"{chunk_text}\n\n"
                    )
                    subtitle_counter += 1
            
            else:
                # Fallback to equal time distribution for methods without word timestamps
                words = text.split()
                total_duration = segment['end'] - segment['start']
                
                # Calculate time per word
                time_per_word = total_duration / len(words) if words else 1
                
                # Group words into chunks of 4
                for i in range(0, len(words), 4):
                    chunk_words = words[i:i+4]
                    chunk_text = " ".join(chunk_words)
                    
                    # Calculate timing for this chunk
                    chunk_start = segment['start'] + (i * time_per_word)
                    chunk_end = segment['start'] + ((i + len(chunk_words)) * time_per_word)
                    
                    start_time = self._format_timestamp(chunk_start)
                    end_time = self._format_timestamp(chunk_end)
                    
                    srt_content.append(
                        f"{subtitle_counter}\n"
                        f"{start_time} --> {end_time}\n"
                        f"{chunk_text}\n\n"
                    )
                    subtitle_counter += 1
        
        subtitle_path.write_text(''.join(srt_content), encoding='utf-8')
        return str(subtitle_path)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _apply_subtitles_to_video(self, video_path: str, subtitle_path: str) -> ffmpeg.nodes.FilterNode:
        """
        Apply subtitles to the Minecraft video.
        
        Args:
            video_path: Path to the Minecraft video
            subtitle_path: Path to the SRT subtitle file
            
        Returns:
            FFmpeg filter node with subtitles applied
        """
        input_video = ffmpeg.input(video_path)
        
        # Scale to bottom half dimensions
        video_scaled = (
            input_video
            .video
            .filter('scale', self.output_width, self.half_height, force_original_aspect_ratio='increase')
            .filter('crop', self.output_width, self.half_height)
        )
        
        # Apply subtitles with Minecraft-style red outline
        subtitle_style = (
            "FontName=Arial,"
            "FontSize=28,"
            "Bold=1,"
            "PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H0000FF,"  # Red outline
            "Outline=2,"
            "BorderStyle=0,"           # No background box
            "Alignment=2,"             # Bottom center
            "MarginV=80"               # Move subtitles up by 80 pixels to avoid mobile controls
        )
        
        video_with_subs = video_scaled.filter(
            'subtitles',
            subtitle_path,
            force_style=subtitle_style
        )
        
        return video_with_subs
    
    def _combine_videos(self, top_video: ffmpeg.nodes.FilterNode, 
                       bottom_video: ffmpeg.nodes.FilterNode, 
                       output_path: Optional[str]) -> Path:
        """
        Combine top and bottom videos into final split-screen layout.
        
        Args:
            top_video: FFmpeg node for top video
            bottom_video: FFmpeg node for bottom video 
            output_path: Custom output path
            
        Returns:
            Path to the final video
        """
        if not output_path:
            output_dir = Path("results") / "creator_shorts"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"split_screen_{timestamp}.mp4"
        else:
            output_path = Path(output_path)
        
        # Stack videos vertically for split-screen effect
        combined = ffmpeg.filter([top_video, bottom_video], 'vstack')
        
        # Extract audio from original creator video and boost its volume
        creator_audio = ffmpeg.input(str(self.creator_video_path)).audio.filter('volume', 1.5)
        
        # Output final video with optimal settings for social media
        try:
            ffmpeg.output(
                combined,
                creator_audio,
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                **{
                    'b:v': '8M',  # 8Mbps video bitrate
                    'b:a': '192k',  # 192kbps audio bitrate
                    'r': '30',  # 30 FPS for social media
                    'threads': multiprocessing.cpu_count(),
                }
            ).overwrite_output().run(quiet=True)
        except ffmpeg.Error as e:
            stderr = getattr(e, 'stderr', b'')
            raise RuntimeError(f"Video composition failed: {stderr.decode('utf8') if isinstance(stderr, bytes) else str(e)}")
        
        return output_path


def create_advanced_short(creator_video_path: str, output_path: Optional[str] = None) -> str:
    """
    Convenience function to create an advanced split-screen short video.
    
    Args:
        creator_video_path: Path to the creator's landscape video
        output_path: Optional custom output path
        
    Returns:
        Path to the created short video
    """
    composer = AdvancedVideoComposer(creator_video_path)
    return str(composer.create_split_screen_video(output_path))


if __name__ == "__main__":
    # Example usage
    creator_video = "path/to/your/landscape/video.mp4"
    output = create_advanced_short(creator_video)
    print(f"Advanced split-screen video saved to: {output}")