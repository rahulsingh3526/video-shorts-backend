from typing import Tuple, Dict, List
from pathlib import Path
import re

from rich.console import Console
from moviepy.audio.io.AudioFileClip import AudioFileClip

from TTS.aws_polly import AWSPolly
from TTS.elevenlabs import elevenlabs
from TTS.engine_wrapper import TTSEngine
from TTS.GTTS import GTTS
from TTS.pyttsx import pyttsx
from TTS.streamlabs_polly import StreamlabsPolly
from TTS.TikTok import TikTok
from utils import settings
from utils.console import print_step, print_table

console = Console()

TTSProviders = {
    "GoogleTranslate": GTTS,
    "AWSPolly": AWSPolly,
    "StreamlabsPolly": StreamlabsPolly,
    "TikTok": TikTok,
    "pyttsx": pyttsx,
    "ElevenLabs": elevenlabs,
}


def save_text_to_mp3(text_content: Dict[str, List[str]]) -> Tuple[List[float], int]:
    """Saves text to MP3 files.

    Args:
        text_content (Dict[str, List[str]]): Dictionary containing title and lines from text file

    Returns:
        tuple[List[float], int]: List of audio durations and total number of lines processed
    """

    voice = settings.config["settings"]["tts"]["voice_choice"]
    if str(voice).casefold() in map(lambda _: _.casefold(), TTSProviders):
        provider = get_case_insensitive_key_value(TTSProviders, voice)
    else:
        while True:
            print_step("Please choose one of the following TTS providers: ")
            print_table(TTSProviders)
            choice = input("\n")
            if choice.casefold() in map(lambda _: _.casefold(), TTSProviders):
                provider = get_case_insensitive_key_value(TTSProviders, choice)
                break
            print("Unknown Choice")

    print_step("Processing audio files...")
    
    # Initialize paths and durations
    text_id = re.sub(r"[^\w-]", "", text_content["title"].replace(" ", "_"))[:10]
    base_path = f"assets/temp/{text_id}"
    durations = []
    mp3_path = Path(base_path) / "mp3"
    mp3_path.mkdir(parents=True, exist_ok=True)
    
    def check_existing_audio(filename: str) -> Tuple[bool, float]:
        """Check if audio file exists and get its duration"""
        file_path = mp3_path / filename
        if file_path.exists():
            try:
                clip = AudioFileClip(str(file_path))
                duration = clip.duration
                clip.close()
                return True, duration
            except:
                return False, 0
        return False, 0

    # Handle title audio (always saved as title.mp3)
    title_exists, title_duration = check_existing_audio("title.mp3")
    if title_exists:
        print(f"Using existing title audio: {mp3_path}/title.mp3")
        durations.append(title_duration)
    else:
        print(f"Generating new title audio...")
        title_engine = TTSEngine(provider, text_content, path=base_path)
        title_duration, _ = title_engine.run()
        durations.append(title_duration)

    # Process content lines (saved as 0.mp3 through N.mp3)
    for i, line in enumerate(text_content['lines']):
        audio_file = f"{i}.mp3"
        exists, duration = check_existing_audio(audio_file)
        if exists:
            print(f"Using existing audio for line {i+1} ({audio_file}): {line[:50]}...")
            durations.append(duration)
        else:
            print(f"Generating new audio for line {i+1} ({audio_file}): {line[:50]}...")
            line_engine = TTSEngine(
                provider,
                {'title': line, 'lines': []},
                path=base_path
            )
            duration, _ = line_engine.run()
            durations.append(duration)
            
    # Verify all files were generated
    expected_files = ["title.mp3"] + [f"{i}.mp3" for i in range(len(text_content['lines']))]
    missing_files = [f for f in expected_files if not (mp3_path / f).exists()]
    if missing_files:
        print("Warning: Missing audio files:", missing_files)
        
    return durations, len(text_content['lines']) + 1  # +1 for title


def get_case_insensitive_key_value(input_dict, key):
    return next(
        (value for dict_key, value in input_dict.items() if dict_key.lower() == key.lower()),
        None,
    )
