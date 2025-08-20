"""
Refactored final_video module with robust Path handling and clearer structure.

Notes:
- Uses pathlib.Path for all path operations.
- Writes concat lists using POSIX-style paths (as_posix) so FFmpeg concat demuxer works on Windows.
- Avoids mixing strings and Path objects with the "/" operator.
- Doesn't run code on import; use the `example_usage` in the __main__ guard as a template.
- Raises exceptions (RuntimeError) on fatal errors instead of calling exit(1) so callers can handle errors.

This file assumes the following exist in your project:
- settings.config (same structure as before)
- helper functions: print_step, print_substep, get_start_and_end_times, prepare_background (or you can use the one here)
- moviepy and ffmpeg-python installed if you use chop_background's moviepy code path

You can paste this file into your project replacing the original file or use it to copy-paste improved path-handling parts.
"""

from __future__ import annotations

import multiprocessing
import os
import re
import tempfile
import textwrap
from text_reader.text_reader import TextReader
import time
from pathlib import Path
from typing import Dict, Final, Tuple, List, Optional

import ffmpeg
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

# Optional imports used by chop_background. Keep them lazy-imported if you don't always need them.
try:
    from moviepy.editor import AudioFileClip, VideoFileClip
except Exception:
    AudioFileClip = None  # type: ignore
    VideoFileClip = None  # type: ignore

from utils import settings
from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.fonts import getheight
from utils.thumbnail import create_thumbnail
from utils.videos import save_data

console = Console()


# -----------------------------
# Helper utilities
# -----------------------------

def ensure_dir(path: Path) -> None:
    """Create directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def sanitize_id(raw: str) -> str:
    """Return a filesystem-safe id derived from raw input."""
    # keep letters, digits, dash and underscore
    return re.sub(r"[^\w-]", "_", raw)


def _create_subtitles_from_transcription(transcription_data: List[Dict]) -> str:
    """
    Create SRT subtitle file using actual speech timing (same as video-to-shorts).
    
    Args:
        transcription_data: List of transcription segments with timestamps and word data
        
    Returns:
        SRT subtitle content
    """
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
                
                start_time = _format_timestamp(chunk_start)
                end_time = _format_timestamp(chunk_end)
                
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
                
                start_time = _format_timestamp(chunk_start)
                end_time = _format_timestamp(chunk_end)
                
                srt_content.append(
                    f"{subtitle_counter}\n"
                    f"{start_time} --> {end_time}\n"
                    f"{chunk_text}\n\n"
                )
                subtitle_counter += 1
    
    return ''.join(srt_content)


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def posix_quoted(path: Path) -> str:
    """Return a POSIX-style quoted path for use in ffmpeg concat lists.

    FFmpeg concat demuxer prefers forward slashes even on Windows.
    """
    return path.as_posix().replace("'", "\\'")


# -----------------------------
# Core functions (refactored)
# -----------------------------


def prepare_background(reddit_id: str, W: int, H: int) -> Path:
    """Convert background.mp4 to a no-audio, cropped version and return Path.

    Returns the Path to the processed background file.
    """
    temp_dir = Path("assets") / "temp" / sanitize_id(reddit_id)
    ensure_dir(temp_dir)
    input_path = temp_dir / "background.mp4"
    output_path = temp_dir / "background_noaudio.mp4"

    if not input_path.exists():
        raise RuntimeError(f"Background video not found: {input_path}")

    try:
        (
            ffmpeg
            .input(str(input_path))
            .filter("crop", f"ih*({W}/{H})", "ih")
            .output(
                str(output_path),
                an=None,
                **{
                    "c:v": "h264",
                    "b:v": "20M",
                    "b:a": "192k",
                    "threads": multiprocessing.cpu_count(),
                },
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        # surface a clear error string
        stderr = getattr(e, "stderr", b"")
        raise RuntimeError(stderr.decode("utf8") if isinstance(stderr, bytes) else str(e))

    return output_path


def merge_background_audio(audio: ffmpeg.nodes.InputNode, text_id: str) -> ffmpeg.nodes.FilterNode:
    """Mix the primary audio with the chopped background audio if configured.

    Returns a ffmpeg filter node representing the final audio stream.
    """
    background_audio_volume = settings.config["settings"]["background"]["background_audio_volume"]
    if background_audio_volume == 0:
        return audio

    bg_path = Path("assets") / "temp" / sanitize_id(text_id) / "background.mp3"
    if not bg_path.exists():
        raise RuntimeError(f"Background audio expected at {bg_path} but not found")

    # Apply 30% volume reduction to background audio only, keep main audio at original level
    bg_audio = ffmpeg.input(str(bg_path)).filter("volume", background_audio_volume * 0.4)
    merged_audio = ffmpeg.filter([audio, bg_audio], "amix", duration="longest")
    return merged_audio


def make_final_video(
    number_of_segments: int,
    audio_durations: List[float],
    text_content: Dict[str, List[str]],
    background_config: Dict[str, Tuple],
    text_id_override: Optional[str] = None,
    transcription_data: Optional[List[Dict]] = None,
) -> Path:
    """Creates the final video with consistent Path handling."""

    W: Final[int] = int(settings.config["settings"]["resolution_w"])
    H: Final[int] = int(settings.config["settings"]["resolution_h"])
    opacity = settings.config["settings"].get("opacity", 1)

    # Use text_id_override if provided, otherwise generate from content
    text_id = text_id_override or ''.join(e for e in text_content.get('title', 'video') if e.isalnum())[:15]

    allow_only_tts_folder: bool = (
        settings.config["settings"]["background"]["enable_extra_audio"]
        and settings.config["settings"]["background"]["background_audio_volume"] != 0
    )

    print_step("Creating the final video 🎥")

    # Prepare background clip
    background_noaudio_path = prepare_background(text_id, W=W, H=H)
    background_clip = ffmpeg.input(str(background_noaudio_path))

    # Temp directory paths
    temp_dir = Path("assets") / "temp" / text_id
    mp3_dir = temp_dir / "mp3"
    ensure_dir(temp_dir)

    if not mp3_dir.exists():
        raise RuntimeError(f"MP3 directory missing: {mp3_dir}")

    # Build concat list
    concat_list_path = temp_dir / "concat_list.txt"
    with concat_list_path.open("w", encoding="utf-8") as f:
        for i in range(number_of_segments):
            filename = "title.mp3" if i == 0 else f"{i-1}.mp3"
            audio_file = mp3_dir / filename
            if not audio_file.exists():
                raise RuntimeError(f"Audio file missing: {audio_file}")
            f.write(f"file '{posix_quoted(audio_file.resolve())}'\n")

    # Concatenate audio
    audio_path = temp_dir / "audio.mp3"
    try:
        (
            ffmpeg
            .input(str(concat_list_path), format="concat", safe=0)
            .output(str(audio_path), acodec="copy")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        stderr = getattr(e, "stderr", b"")
        raise RuntimeError("Error concatenating audio: " + (stderr.decode("utf8") if isinstance(stderr, bytes) else str(e)))

    console.log(f"[bold green] Video Will Be: {sum(audio_durations)} Seconds Long")

    audio = ffmpeg.input(str(audio_path))
    final_audio = merge_background_audio(audio, text_id)

    # Subtitles
    srt_dir = temp_dir / "subtitles"
    ensure_dir(srt_dir)
    srt_path = srt_dir / "subs.srt"
    try:
        if transcription_data:
            # Use actual transcription data for accurate word-level timing
            print_substep("🎯 Using Whisper transcription for precise subtitle timing")
            srt_content = _create_subtitles_from_transcription(transcription_data)
        else:
            # Fallback to text reader with estimated timing
            print_substep("📝 Using estimated timing for subtitles")
            temp_story_path = temp_dir / "current_story.txt"
            with temp_story_path.open("w", encoding="utf-8") as f:
                f.write(text_content["title"] + "\n")
                for line in text_content["lines"]:
                    f.write(line + "\n")
            
            text_reader = TextReader(str(temp_story_path))
            srt_content = text_reader.generate_subtitle_data(audio_durations)
        
        srt_path.write_text(srt_content, encoding="utf-8")
        # Apply subtitles with smaller font size for better readability
        subtitle_style = (
            "FontName=Arial,"
            "FontSize=20,"  # Reduced from 28 to 20
            "Bold=1,"
            "PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,"
            "Outline=2,"  # Reduced outline thickness
            "BorderStyle=0,"  # No background box
            "Alignment=2,"    # Bottom center
            "MarginV=80"      # Move subtitles up by 80 pixels to avoid mobile controls
        )
        background_clip = background_clip.filter(
            "subtitles",
            str(srt_path),
            force_style=subtitle_style
        )
    except Exception as e:
        print_substep(f"Subtitle generation skipped due to error: {e}", "yellow")

    # Background attribution
    try:
        text = f"Background by {background_config['video'][2]}"
        background_clip = ffmpeg.drawtext(
            background_clip,
            text=text,
            x="(w-text_w)",
            y="(h-text_h)",
            fontsize=5,
            fontcolor="White",
            fontfile=str(Path("fonts") / "Roboto-Regular.ttf"),
        )
    except Exception:
        pass

    background_clip = background_clip.filter("scale", W, H)

    # Output path
    subreddit = "custom"
    results_dir = Path("results") / subreddit
    ensure_dir(results_dir)

    safe_filename = re.sub(r"[^\w-]", "_", (text_content.get("title") or "video")[:251])
    output_path = results_dir / f"{safe_filename}.mp4"

    # Render main video
    try:
        ffmpeg.output(
            background_clip,
            final_audio,
            str(output_path),
            f="mp4",
            **{
                "c:v": "h264",
                "b:v": "20M",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
            },
        ).overwrite_output().run(quiet=True)
    except ffmpeg.Error as e:
        stderr = getattr(e, "stderr", b"")
        raise RuntimeError("FFmpeg render failed: " + (stderr.decode("utf8") if isinstance(stderr, bytes) else str(e)))

    # OnlyTTS copy
    if allow_only_tts_folder:
        only_tts_dir = results_dir / "OnlyTTS"
        ensure_dir(only_tts_dir)
        tts_path = only_tts_dir / (output_path.name)
        try:
            ffmpeg.output(
                background_clip,
                audio,
                str(tts_path),
                f="mp4",
                **{
                    "c:v": "h264",
                    "b:v": "20M",
                    "b:a": "192k",
                    "threads": multiprocessing.cpu_count(),
                },
            ).overwrite_output().run(quiet=True)
        except ffmpeg.Error as e:
            stderr = getattr(e, "stderr", b"")
            print_substep("Rendering OnlyTTS failed: " + (stderr.decode("utf8") if isinstance(stderr, bytes) else str(e)))

    # Save metadata and cleanup
    save_data(output_path.name, text_content.get("title", ""), text_id, background_config["video"][2])
    cleanups = cleanup(text_id)
    print_substep(f"Removed {cleanups} temporary files 🗑")
    print_step("Done! 🎉 The video is in the results folder 📁")
    return output_path


# -----------------------------
# Chop background (moviepy path) - uses Path properly
# -----------------------------


def chop_background(background_config: Dict[str, Tuple], video_length: int, text_object: dict) -> str:
    """Generates the background audio and footage to be used in the video.

    This function mirrors your original logic but ensures consistent Path use.
    Returns the identifier/name of the chosen background video.
    """
    if AudioFileClip is None or VideoFileClip is None:
        raise RuntimeError("moviepy not available; chop_background requires moviepy installed")

    text_id = sanitize_id(text_object.get("thread_id", "default"))
    temp_dir = Path("assets") / "temp" / text_id
    ensure_dir(temp_dir)

    bg_audio_conf = background_config.get("audio")
    if bg_audio_conf:
        audio_choice = f"{bg_audio_conf[2]}-{bg_audio_conf[1]}"
        audio_path = Path("assets") / "backgrounds" / "audio" / audio_choice
        if settings.config["settings"]["background"]["background_audio_volume"] != 0:
            print_step("Finding a spot in the backgrounds audio to chop...✂️")
            background_audio = AudioFileClip(str(audio_path))
            start_time_audio, end_time_audio = get_start_and_end_times(video_length, background_audio.duration)
            bg_segment = background_audio.subclip(start_time_audio, end_time_audio)
            out_audio = temp_dir / "background.mp3"
            bg_segment.write_audiofile(str(out_audio))

    # Chop video
    video_choice_conf = background_config.get("video")
    if not video_choice_conf:
        raise RuntimeError("background_config missing 'video' key")
    video_choice = f"{video_choice_conf[2]}-{video_choice_conf[1]}"
    video_path = Path("assets") / "backgrounds" / "video" / video_choice
    print_step("Finding a spot in the backgrounds video to chop...✂️")

    # Use moviepy safe extraction
    try:
        with VideoFileClip(str(video_path)) as video:
            start_time_video, end_time_video = get_start_and_end_times(video_length, video.duration)
            new = video.subclip(start_time_video, end_time_video)
            out_video = temp_dir / "background.mp4"
            new.write_videofile(str(out_video), codec="libx264")
            print_substep("Background video chopped successfully!", style="bold green")
    except Exception as e:
        print_substep(f"Error during video processing: {e}")
        raise

    return video_choice_conf[2]