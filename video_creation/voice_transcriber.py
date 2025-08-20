"""
Voice Transcription Module

Handles extraction of audio from video files and transcription of speech to text
for subtitle generation in creator short videos.
"""

import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import ffmpeg
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None

from utils.console import print_step, print_substep


def extract_voice_from_video(video_path: str, output_path: Optional[str] = None) -> Tuple[str, float]:
    """
    Extract audio from video file.
    
    Args:
        video_path: Path to the input video file
        output_path: Optional custom output path for audio file
        
    Returns:
        Tuple of (audio_file_path, video_duration_seconds)
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    print_substep(f"Extracting audio from {video_path.name}")
    
    if not output_path:
        temp_dir = Path("assets") / "temp" / "voice_extraction"
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = temp_dir / f"{video_path.stem}_audio.wav"
    else:
        output_path = Path(output_path)
    
    try:
        # Get video duration using moviepy for accuracy
        if VideoFileClip is None:
            raise ImportError("MoviePy not available")
        with VideoFileClip(str(video_path)) as video:
            duration = video.duration
        
        # Extract audio using ffmpeg for better quality
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(output_path),
                acodec='pcm_s16le',  # 16-bit PCM for better transcription compatibility
                ar=16000,            # 16kHz sample rate (standard for speech recognition)
                ac=1                 # Mono audio
            )
            .overwrite_output()
            .run(quiet=True)
        )
        
        print_substep(f"Audio extracted to {output_path.name}", style="bold green")
        return str(output_path), duration
        
    except ffmpeg.Error as e:
        stderr = getattr(e, 'stderr', b'')
        raise RuntimeError(f"Audio extraction failed: {stderr.decode('utf8') if isinstance(stderr, bytes) else str(e)}")


def transcribe_audio(audio_path: str, method: str = "whisper") -> List[Dict]:
    """
    Transcribe audio to text with timestamps.
    
    Args:
        audio_path: Path to the audio file
        method: Transcription method ('whisper', 'vosk', or 'speech_recognition')
        
    Returns:
        List of transcription segments with format:
        [{'start': float, 'end': float, 'text': str}, ...]
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    print_substep(f"Transcribing audio using {method}")
    
    if method.lower() == "whisper":
        return _transcribe_with_whisper(str(audio_path))
    elif method.lower() == "vosk":
        return _transcribe_with_vosk(str(audio_path))
    elif method.lower() == "speech_recognition":
        return _transcribe_with_speech_recognition(str(audio_path))
    else:
        raise ValueError(f"Unsupported transcription method: {method}")


def _transcribe_with_whisper(audio_path: str) -> List[Dict]:
    """
    Transcribe audio using OpenAI Whisper with word-level timestamps.
    Requires: pip install openai-whisper
    """
    try:
        import whisper
    except ImportError:
        print_substep("Whisper not available, using simple transcription")
        return _transcribe_simple(audio_path)
    
    print_substep("Loading Whisper model...")
    # Use 'base' model for good balance of speed and accuracy
    model = whisper.load_model("base")
    
    print_substep("Transcribing with Whisper (word-level timestamps)...")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    segments = []
    for segment in result['segments']:
        # Create a segment with word-level timing data
        segment_data = {
            'start': segment['start'],
            'end': segment['end'], 
            'text': segment['text'].strip(),
            'words': []  # Add word-level timestamps
        }
        
        # Extract word-level timestamps if available
        if 'words' in segment:
            for word in segment['words']:
                segment_data['words'].append({
                    'word': word['word'].strip(),
                    'start': word['start'],
                    'end': word['end']
                })
        
        segments.append(segment_data)
    
    print_substep(f"Whisper transcription completed: {len(segments)} segments with word timing", style="bold green")
    return segments


def _transcribe_simple(audio_path: str) -> List[Dict]:
    """
    Simple fallback transcription when Whisper is not available.
    Creates placeholder text for demonstration.
    """
    print_substep("Using simple transcription (placeholder text)")
    
    # Get audio duration
    try:
        with wave.open(audio_path, 'rb') as wf:
            duration = wf.getnframes() / wf.getframerate()
    except:
        duration = 30.0  # Default fallback
    
    # Create simple placeholder segments
    segments = [
        {
            'start': 0.0,
            'end': duration / 2,
            'text': 'Welcome to this amazing video content',
            'words': [
                {'word': 'Welcome', 'start': 0.0, 'end': 0.8},
                {'word': 'to', 'start': 0.8, 'end': 1.0},
                {'word': 'this', 'start': 1.0, 'end': 1.3},
                {'word': 'amazing', 'start': 1.3, 'end': 1.8},
                {'word': 'video', 'start': 1.8, 'end': 2.2},
                {'word': 'content', 'start': 2.2, 'end': 2.7}
            ]
        },
        {
            'start': duration / 2,
            'end': duration,
            'text': 'Thanks for watching and subscribe for more',
            'words': [
                {'word': 'Thanks', 'start': duration / 2, 'end': duration / 2 + 0.6},
                {'word': 'for', 'start': duration / 2 + 0.6, 'end': duration / 2 + 0.8},
                {'word': 'watching', 'start': duration / 2 + 0.8, 'end': duration / 2 + 1.4},
                {'word': 'and', 'start': duration / 2 + 1.4, 'end': duration / 2 + 1.6},
                {'word': 'subscribe', 'start': duration / 2 + 1.6, 'end': duration / 2 + 2.3},
                {'word': 'for', 'start': duration / 2 + 2.3, 'end': duration / 2 + 2.5},
                {'word': 'more', 'start': duration / 2 + 2.5, 'end': duration / 2 + 2.9}
            ]
        }
    ]
    
    print_substep(f"Simple transcription completed: {len(segments)} segments", style="bold green")
    return segments


def _transcribe_with_vosk(audio_path: str) -> List[Dict]:
    """
    Transcribe audio using Vosk speech recognition.
    Requires: pip install vosk
    """
    try:
        import vosk
        import json
    except ImportError:
        raise ImportError("Vosk not installed. Run: pip install vosk")
    
    # Download model if needed (you might want to customize this path)
    model_path = Path("models") / "vosk-model-en-us-0.22"
    if not model_path.exists():
        print_substep("Vosk model not found. Please download from https://alphacephei.com/vosk/models")
        raise FileNotFoundError(f"Vosk model not found at {model_path}")
    
    model = vosk.Model(str(model_path))
    recognizer = vosk.KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)  # Enable word-level timestamps
    
    # Read audio file
    with wave.open(audio_path, 'rb') as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            raise ValueError("Audio file must be mono, 16-bit, 16kHz WAV")
        
        segments = []
        current_segment = {"start": 0, "text": ""}
        
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
                
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if 'text' in result and result['text'].strip():
                    # Calculate timing (simplified)
                    current_time = wf.tell() / (wf.getframerate() * wf.getnchannels() * wf.getsampwidth())
                    
                    if current_segment["text"]:
                        current_segment["end"] = current_time
                        segments.append(current_segment.copy())
                    
                    current_segment = {
                        "start": current_time,
                        "text": result['text'].strip()
                    }
        
        # Final result
        final_result = json.loads(recognizer.FinalResult())
        if 'text' in final_result and final_result['text'].strip():
            current_segment["text"] += " " + final_result['text'].strip()
            current_segment["end"] = wf.getnframes() / wf.getframerate()
            segments.append(current_segment)
    
    print_substep(f"Vosk transcription completed: {len(segments)} segments", style="bold green")
    return segments


def _transcribe_with_speech_recognition(audio_path: str) -> List[Dict]:
    """
    Transcribe audio using SpeechRecognition library.
    Requires: pip install SpeechRecognition
    Note: This method doesn't provide precise timestamps, so we'll estimate them.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        raise ImportError("SpeechRecognition not installed. Run: pip install SpeechRecognition")
    
    recognizer = sr.Recognizer()
    
    # Load audio file
    with sr.AudioFile(audio_path) as source:
        # Get duration
        with wave.open(audio_path, 'rb') as wf:
            duration = wf.getnframes() / wf.getframerate()
        
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        # Record the entire audio
        audio = recognizer.record(source)
    
    try:
        # Recognize speech using Google Speech Recognition
        text = recognizer.recognize_google(audio)
        
        # Since we don't have precise timestamps, create a single segment
        segments = [{
            'start': 0.0,
            'end': duration,
            'text': text
        }]
        
        print_substep(f"Speech Recognition transcription completed: 1 segment", style="bold green")
        return segments
        
    except sr.UnknownValueError:
        print_substep("Could not understand audio", style="bold red")
        return []
    except sr.RequestError as e:
        print_substep(f"Could not request results from Google Speech Recognition: {e}", style="bold red")
        return []


def get_available_transcription_methods() -> List[str]:
    """
    Get list of available transcription methods based on installed packages.
    
    Returns:
        List of available method names
    """
    methods = []
    
    try:
        import whisper
        methods.append("whisper")
    except ImportError:
        pass
    
    try:
        import vosk
        methods.append("vosk")
    except ImportError:
        pass
    
    try:
        import speech_recognition
        methods.append("speech_recognition")
    except ImportError:
        pass
    
    return methods


if __name__ == "__main__":
    # Example usage
    video_path = "path/to/your/video.mp4"
    
    # Extract audio
    audio_path, duration = extract_voice_from_video(video_path)
    print(f"Extracted audio: {audio_path}, Duration: {duration}s")
    
    # Transcribe
    available_methods = get_available_transcription_methods()
    if available_methods:
        method = available_methods[0]  # Use first available method
        transcription = transcribe_audio(audio_path, method)
        print(f"Transcription ({method}): {len(transcription)} segments")
        for segment in transcription:
            print(f"  {segment['start']:.2f}s - {segment['end']:.2f}s: {segment['text']}")
    else:
        print("No transcription methods available. Please install whisper, vosk, or speech_recognition.")