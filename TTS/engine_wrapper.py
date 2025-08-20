import os
import re
from pathlib import Path
from typing import Tuple

import numpy as np
import translators
from moviepy.audio.AudioClip import AudioClip
# from moviepy.audio.fx.volumex import volumex
from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
from moviepy.audio.io.AudioFileClip import AudioFileClip
from rich.progress import track

from utils import settings
from utils.console import print_step, print_substep
from utils.voice import sanitize_text

DEFAULT_MAX_LENGTH: int = (
    50  # Video length variable, edit this on your own risk. It should work, but it's not supported
)


class TTSEngine:
    """Calls the given TTS engine to reduce code duplication and allow multiple TTS engines.

    Args:
        tts_module            : The TTS module. Your module should handle the TTS itself and saving to the given path under the run method.
        reddit_object         : The reddit object that contains the posts to read.
        path (Optional)       : The unix style path to save the mp3 files to. This must not have leading or trailing slashes.
        max_length (Optional) : The maximum length of the mp3 files in total.

    Notes:
        tts_module must take the arguments text and filepath.
    """

    def __init__(
        self,
        tts_module,
        text_content: dict,
        path: str = "assets/temp/",
        max_length: int = DEFAULT_MAX_LENGTH,
        last_clip_length: int = 0,
    ):
        self.tts_module = tts_module()
        self.text_content = text_content
        
        # Sanitize the text_id only if it's a title, otherwise reuse existing ID
        if 'lines' in text_content and text_content['lines']:
            # This is the main content, generate new ID
            self.text_id = re.sub(r"[^\w-]", "", text_content["title"].replace(" ", "_"))[:10]
        else:
            # This is a line or single text, use parent path's ID
            parent_path = Path(path)
            self.text_id = parent_path.parts[-1] if parent_path.parts else "default"
            
        # Ensure proper path formatting
        mp3_path = Path(path) / "mp3"
        mp3_path.mkdir(parents=True, exist_ok=True)
        self.path = str(mp3_path)
        self.max_length = max_length
        self.length = 0
        self.last_clip_length = last_clip_length

    def add_periods(self):
        """Adds periods to the end of paragraphs and cleans text for better TTS"""
        for line in self.text_content["lines"]:
            # remove links
            regex_urls = r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
            line = re.sub(regex_urls, " ", line)
            line = line.replace("\n", ". ")
            line = re.sub(r"\bAI\b", "A.I", line)
            line = re.sub(r"\bAGI\b", "A.G.I", line)
            if line[-1] != ".":
                line += "."
            line = line.replace(". . .", ".")
            line = line.replace(".. . ", ".")
            line = line.replace(". . ", ".")
            line = re.sub(r'\."\.', '".', line)

    def run(self) -> Tuple[int, int]:
        # Ensure output directory exists and is writable
        mp3_path = Path(self.path)
        try:
            mp3_path.mkdir(parents=True, exist_ok=True)
            # Test write permissions by creating a temp file
            test_file = mp3_path / '.test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            print(f"Error: Cannot create/write to directory {mp3_path}")
            print(f"Details: {str(e)}")
            raise

        print_step(f"Saving audio to: {self.path}")
        self.add_periods()
        self.call_tts("title", process_text(self.text_content["title"]))
        idx = 0

        # Process each line of text
        for idx, line in track(enumerate(self.text_content["lines"]), "Saving..."):
            # Stop if we exceed max length
            if self.length > self.max_length and idx > 1:
                self.length -= self.last_clip_length
                idx -= 1
                break
                
            # Split long lines if needed
            if len(line) > self.tts_module.max_chars:
                self.split_post(line, idx)
            else:
                self.call_tts(f"{idx}", process_text(line))

        # Verify all MP3 files were generated
        file_count = self._verify_audio_files()
        if file_count == idx + 1:  # +1 for title
            print_substep(f"Successfully generated {file_count} audio files", style="bold green")
            return self.length, idx
        else:
            print_substep(f"Warning: Expected {idx + 1} audio files but found {file_count}", style="bold red")
            print_substep("Missing files may cause video generation to fail", style="bold red")
            return self.length, idx
            
    def _verify_audio_files(self) -> int:
        """Verify all expected MP3 files were generated"""
        mp3_dir = Path(self.path)
        if not mp3_dir.exists():
            return 0
            
        mp3_files = list(mp3_dir.glob("*.mp3"))
        print_substep(f"Found {len(mp3_files)} audio files in {mp3_dir}")
        return len(mp3_files)

    def split_post(self, text: str, idx):
        split_files = []
        split_text = [
            x.group().strip()
            for x in re.finditer(
                r" *(((.|\n){0," + str(self.tts_module.max_chars) + "})(\.|.$))", text
            )
        ]
        self.create_silence_mp3()

        idy = None
        for idy, text_cut in enumerate(split_text):
            newtext = process_text(text_cut)
            # print(f"{idx}-{idy}: {newtext}\n")

            if not newtext or newtext.isspace():
                print("newtext was blank because sanitized split text resulted in none")
                continue
            else:
                self.call_tts(f"{idx}-{idy}.part", newtext)
                with open(f"{self.path}/list.txt", "w") as f:
                    for idz in range(0, len(split_text)):
                        f.write("file " + f"'{idx}-{idz}.part.mp3'" + "\n")
                    split_files.append(str(f"{self.path}/{idx}-{idy}.part.mp3"))
                    f.write("file " + f"'silence.mp3'" + "\n")

                os.system(
                    "ffmpeg -f concat -y -hide_banner -loglevel panic -safe 0 "
                    + "-i "
                    + f"{self.path}/list.txt "
                    + "-c copy "
                    + f"{self.path}/{idx}.mp3"
                )
        try:
            for i in range(0, len(split_files)):
                os.unlink(split_files[i])
        except FileNotFoundError as e:
            print("File not found: " + e.filename)
        except OSError:
            print("OSError")

    def call_tts(self, filename: str, text: str):
        # For title text, use title.mp3, otherwise use numeric index
        output_filename = "title" if filename == "title" else filename
        filepath = f"{self.path}/{output_filename}.mp3"
        
        print(f"Generating audio for {output_filename}.mp3...")
        self.tts_module.run(
            text,
            filepath=filepath,
            random_voice=settings.config["settings"]["tts"]["random_voice"],
        )
        # try:
        #     self.length += MP3(f"{self.path}/{filename}.mp3").info.length
        # except (MutagenError, HeaderNotFoundError):
        #     self.length += sox.file_info.duration(f"{self.path}/{filename}.mp3")
        try:
            clip = AudioFileClip(f"{self.path}/{filename}.mp3")
            self.last_clip_length = clip.duration
            self.length += clip.duration
            clip.close()
        except:
            self.length = 0

    def create_silence_mp3(self):
        silence_duration = settings.config["settings"]["tts"]["silence_duration"]
        silence = AudioClip(
            make_frame=lambda t: np.sin(440 * 2 * np.pi * t),
            duration=silence_duration,
            fps=44100,
        )
        silence = MultiplyVolume(silence, 0)
        silence.write_audiofile(f"{self.path}/silence.mp3", fps=44100, verbose=False, logger=None)


def process_text(text: str, clean: bool = True):
    lang = "en"
    # lang = settings.config["reddit"]["thread"]["post_lang"]
    new_text = sanitize_text(text) if clean else text
    if lang:
        print_substep("Translating Text...")
        translated_text = translators.translate_text(text, translator="google", to_language=lang)
        new_text = sanitize_text(translated_text)
    return new_text
