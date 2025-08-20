"""
Video Composer for Creator Short Videos

This module handles the composition of creator videos with Minecraft-style gameplay footage,
creating a split-screen short video format where:
- Top half: Original creator landscape video 
- Bottom half: Minecraft-style gameplay footage with transcribed subtitles
"""

from __future__ import annotations

import multiprocessing
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ffmpeg
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None

try:
    from utils import settings
    from utils.console import print_step, print_substep
    from video_creation.background import get_background_config, download_background_video, chop_background
    from video_creation.voice_transcriber import extract_voice_from_video, transcribe_audio
except ImportError as e:
    print(f"Import error: {e}")
    raise


class VideoComposer:
    """Handles composition of split-screen creator videos with gameplay footage."""
    
    def __init__(self, creator_video_path: str, output_resolution: Tuple[int, int] = (1080, 1920), background_type: str = "minecraft-2", background_start_time: Optional[float] = None, prefer_bright: bool = True, background_music_path: Optional[str] = None, music_volume: float = 0.3, output_fps: int = 30):
        """
        Initialize VideoComposer.
        
        Args:
            creator_video_path: Path to the creator's landscape video
            output_resolution: Target resolution (width, height) for the output short video
            background_type: Type of background video to use (see background_videos.json for options)
            background_start_time: Specific start time for background video (None for auto-selection)
            prefer_bright: Whether to prefer brighter sections of the background video
            background_music_path: Path to background music file (None to disable)
            music_volume: Volume level for background music (0.0-1.0)
            output_fps: Output frame rate for final video (default: 30)
        """
        self.creator_video_path = Path(creator_video_path)
        self.output_width, self.output_height = output_resolution
        self.half_height = self.output_height // 2
        self.transcription_method = "auto"  # Default transcription method
        self.background_type = background_type  # Background video type
        self.background_start_time = background_start_time  # Custom start time
        self.prefer_bright = prefer_bright  # Prefer bright sections
        self.background_music_path = background_music_path  # Background music file
        self.music_volume = music_volume  # Music volume level
        self.output_fps = output_fps  # Output frame rate
        
        if not self.creator_video_path.exists():
            raise FileNotFoundError(f"Creator video not found: {creator_video_path}")
    
    def create_short_video(self, output_path: Optional[str] = None) -> Path:
        """
        Create a split-screen short video combining creator video and Minecraft footage.
        
        Args:
            output_path: Custom output path, if None will auto-generate
            
        Returns:
            Path to the created short video
        """
        print_step("🎬 Starting creator short video composition")
        
        # Step 1: Extract and transcribe audio from creator video
        print_step("🎤 Extracting voice from creator video")
        audio_path, video_duration = extract_voice_from_video(str(self.creator_video_path))
        
        print_step("📝 Transcribing voice to text")
        transcription_data = transcribe_audio(audio_path, method=self.transcription_method)
        
        # Step 2: Process creator video for top half
        print_step("📹 Processing creator video for top section")
        top_video = self._prepare_creator_video_for_top()
        
        # Step 3: Generate background footage for bottom half
        print_step(f"🎮 Generating {self.background_type} footage for bottom section")
        bottom_video = self._generate_background_footage(video_duration)
        
        # Step 4: Create subtitles for bottom video
        print_step("💬 Creating subtitles from transcription")
        subtitle_path = self._create_subtitles_from_transcription(transcription_data)
        
        # Step 5: Apply subtitles to bottom video
        bottom_video_with_subs = self._apply_subtitles_to_video(bottom_video, subtitle_path)
        
        # Step 6: Generate background music clip if enabled
        background_music_clip = None
        if self.background_music_path:
            print_step("🎵 Generating background music clip")
            background_music_clip = self._generate_background_music_clip(video_duration)
        
        # Step 7: Combine top and bottom videos
        print_step("🔧 Combining videos into split-screen layout")
        output_path = self._combine_videos(top_video, bottom_video_with_subs, output_path, background_music_clip)
        
        print_step("✅ Creator short video completed!")
        return output_path
    
    def _prepare_creator_video_for_top(self) -> ffmpeg.nodes.FilterNode:
        """
        Prepare the creator video for the top half of the short video.
        Scales to fit width with minimal cropping, ensuring no gaps with bottom video.
        
        Returns:
            FFmpeg filter node for the processed top video
        """
        # Load creator video
        input_video = ffmpeg.input(str(self.creator_video_path))
        
        # Scale to fit width exactly, then crop height if needed to fit half_height
        # This ensures the video fills the entire width with minimal left/right cropping
        top_video = (
            input_video
            .video
            .filter('scale', self.output_width, -1)  # Scale to exact width, maintain aspect ratio
            .filter('scale', self.output_width, self.half_height, force_original_aspect_ratio='increase')  # Scale to fill
            .filter('crop', self.output_width, self.half_height)  # Crop to exact dimensions
        )
        
        return top_video
    
    def _generate_background_footage(self, duration: float) -> str:
        """
        Generate engaging background footage for the bottom half.
        
        Args:
            duration: Required duration in seconds
            
        Returns:
            Path to the generated background footage
        """
        # Load background options
        import json
        backgrounds_file = Path("utils") / "background_videos.json"
        with open(backgrounds_file, 'r') as f:
            background_options = json.load(f)
        
        # Get the specified background or fall back to a default
        if self.background_type not in background_options:
            print_substep(f"Background '{self.background_type}' not found, using minecraft-2")
            self.background_type = "minecraft-2"
        
        background_config = background_options[self.background_type]
        filename = f"{background_config[2]}-{background_config[1]}"
        background_path = Path("assets") / "backgrounds" / "video" / filename
        
        # Download if not exists
        if not background_path.exists():
            print_substep(f"Downloading {self.background_type} background...")
            try:
                from video_creation.background import download_background_video
                download_background_video(tuple(background_config))
            except Exception as e:
                print_substep(f"Failed to download background: {e}")
                # Fall back to existing Minecraft footage
                background_path = Path("assets") / "backgrounds" / "video" / "Itslpsn-minecraft-2.mp4"
                if not background_path.exists():
                    raise RuntimeError("No background footage available")
        
        # Create temp directory
        temp_dir = Path("assets") / "temp" / "creator_short_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Use moviepy to extract the required duration
        output_path = temp_dir / "background.mp4"
        
        if VideoFileClip is None:
            raise RuntimeError("MoviePy not available for video processing")
            
        # Use brightness analysis to find the best section
        start_time = self._analyze_video_brightness(str(background_path), duration)
        
        with VideoFileClip(str(background_path)) as video:
            # Extract the clip using the analyzed start time
            clip = video.subclip(start_time, start_time + duration)
            clip.write_videofile(str(output_path), codec='libx264', audio=False)
        
        return str(output_path)
    
    def _generate_background_music_clip(self, duration: float) -> Optional[str]:
        """
        Generate a random background music clip of the specified duration.
        
        Args:
            duration: Required duration in seconds
            
        Returns:
            Path to the generated music clip, or None if no background music
        """
        if not self.background_music_path:
            return None
            
        music_path = Path(self.background_music_path)
        if not music_path.exists():
            print_substep(f"⚠️ Background music not found: {music_path}")
            return None
        
        # Create temp directory
        temp_dir = Path("assets") / "temp" / "creator_short_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = temp_dir / "background_music.wav"
        
        try:
            if VideoFileClip is None:
                raise RuntimeError("MoviePy not available for audio processing")
            
            # Use MoviePy to get music duration and extract random clip
            from moviepy.editor import AudioFileClip
            
            with AudioFileClip(str(music_path)) as audio:
                total_duration = audio.duration
                
                # If music is shorter than needed, loop it
                if total_duration <= duration:
                    # Loop the audio to cover the required duration
                    loops_needed = int(duration // total_duration) + 1
                    looped_audio = audio
                    for _ in range(loops_needed - 1):
                        looped_audio = looped_audio.concatenate(audio)
                    
                    # Trim to exact duration
                    final_audio = looped_audio.subclip(0, duration)
                else:
                    # Select random start time for variety
                    max_start = max(0, total_duration - duration)
                    random_start = random.uniform(0, max_start)
                    print_substep(f"🎵 Using music clip starting at {random_start:.1f}s")
                    
                    final_audio = audio.subclip(random_start, random_start + duration)
                
                # Apply volume adjustment
                final_audio = final_audio.volumex(self.music_volume)
                
                # Export as WAV for better compatibility with FFmpeg
                final_audio.write_audiofile(str(output_path), verbose=False, logger=None)
            
            return str(output_path)
            
        except Exception as e:
            print_substep(f"⚠️ Failed to generate background music clip: {e}")
            return None
    
    def _analyze_video_brightness(self, video_path: str, duration: float) -> float:
        """
        Select a random section from the background video for variety.
        
        Args:
            video_path: Path to the video file
            duration: Duration needed for the clip
            
        Returns:
            Random start time for the clip
        """
        try:
            from moviepy.editor import VideoFileClip
            
            with VideoFileClip(video_path) as video:
                total_duration = video.duration
                
                # If specific start time is provided, use it
                if self.background_start_time is not None:
                    max_start = max(0, total_duration - duration)
                    return min(self.background_start_time, max_start)
                
                # If video is shorter than needed, start from beginning
                if total_duration <= duration:
                    return 0
                
                # Always use random selection for variety
                max_start = max(0, total_duration - duration)
                if max_start <= 0:
                    return 0
                
                # Generate a completely random start time
                random_start = random.uniform(0, max_start)
                print_substep(f"🎲 Using random clip starting at {random_start:.1f}s")
                return random_start
                    
        except Exception as e:
            print_substep(f"⚠️ Video analysis failed: {e}, using fallback random selection")
            # Fallback to random selection
            try:
                with VideoFileClip(video_path) as video:
                    max_start = max(0, video.duration - duration)
                    return random.uniform(0, max_start) if max_start > 0 else 0
            except:
                return 0
    
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
        
        # Apply subtitles with styling based on background type
        if "minecraft" in self.background_type.lower():
            # Minecraft videos: Red outline only
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
        elif "fall" in self.background_type.lower() or "guys" in self.background_type.lower():
            # Fall Guys videos: Red inner + Yellow outer outline
            subtitle_style = (
                "FontName=Arial,"
                "FontSize=28,"
                "Bold=1,"
                "PrimaryColour=&HFFFFFF,"
                "OutlineColour=&H0000FF,"  # Red inner outline
                "Outline=2,"
                "BackColour=&H00FFFF,"     # Yellow outer outline (shadow)
                "Shadow=3,"                # Yellow shadow thickness
                "BorderStyle=0,"           # No background box
                "Alignment=2,"             # Bottom center
                "MarginV=80"               # Move subtitles up by 80 pixels to avoid mobile controls
            )
        else:
            # Default: Red outline only
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
                       output_path: Optional[str],
                       background_music_path: Optional[str] = None) -> Path:
        """
        Combine top and bottom videos into final split-screen layout with subtle separation.
        
        Args:
            top_video: FFmpeg node for top video
            bottom_video: FFmpeg node for bottom video 
            output_path: Custom output path
            background_music_path: Path to background music clip
            
        Returns:
            Path to the final video
        """
        if not output_path:
            output_dir = Path("results") / "creator_shorts"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"short_{self.creator_video_path.stem}.mp4"
        else:
            output_path = Path(output_path)
        
        # Stack videos vertically with no gaps for seamless connection
        combined = ffmpeg.filter([top_video, bottom_video], 'vstack')
        
        # Extract audio from original creator video and boost its volume
        creator_audio = ffmpeg.input(str(self.creator_video_path)).audio.filter('volume', 1.5)
        
        # Mix background music with creator audio if provided
        if background_music_path and Path(background_music_path).exists():
            print_substep("🎵 Mixing background music with creator audio")
            background_music = ffmpeg.input(background_music_path).audio
            
            # Apply volume reduction to background music only (keep it quiet at 0.7x)
            background_music_quiet = background_music.filter('volume', 0.4)
            
            # Mix the two audio streams (boosted creator voice + quieter background music)
            mixed_audio = ffmpeg.filter([creator_audio, background_music_quiet], 'amix', inputs=2, duration='first')
        else:
            mixed_audio = creator_audio
        
        # Output final video with frame rate limit for social media
        try:
            ffmpeg.output(
                combined,
                mixed_audio,
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                **{
                    'b:v': '8M',
                    'b:a': '192k',
                    'r': str(self.output_fps),  # Use specified frame rate
                    'threads': multiprocessing.cpu_count(),
                }
            ).overwrite_output().run(quiet=True)
        except ffmpeg.Error as e:
            stderr = getattr(e, 'stderr', b'')
            raise RuntimeError(f"Video composition failed: {stderr.decode('utf8') if isinstance(stderr, bytes) else str(e)}")
        
        return output_path


def create_creator_short(creator_video_path: str, output_path: Optional[str] = None, background_music_path: Optional[str] = None, music_volume: float = 0.3, output_fps: int = 30) -> str:
    """
    Convenience function to create a creator short video.
    
    Args:
        creator_video_path: Path to the creator's landscape video
        output_path: Optional custom output path
        background_music_path: Path to background music file (None to disable)
        music_volume: Volume level for background music (0.0-1.0)
        output_fps: Output frame rate for final video (default: 30)
        
    Returns:
        Path to the created short video
    """
    composer = VideoComposer(creator_video_path, background_music_path=background_music_path, music_volume=music_volume, output_fps=output_fps)
    return str(composer.create_short_video(output_path))


if __name__ == "__main__":
    # Example usage
    creator_video = "path/to/your/landscape/video.mp4"
    output = create_creator_short(creator_video)
    print(f"Creator short video saved to: {output}")