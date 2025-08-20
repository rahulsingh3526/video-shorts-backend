import json
import time
import os
from utils import settings
from utils.console import print_step


def check_done(text_id: str) -> bool:
    """Checks if the text content has already been processed

    Args:
        text_id (str): Unique identifier for the text content

    Returns:
        bool: True if content can be processed, False if already done
    """
    with open("./video_creation/data/videos.json", "r", encoding="utf-8") as done_vids_raw:
        done_videos = json.load(done_vids_raw)
    for video in done_videos:
        if video["id"] == text_id:
            print_step("This content has already been processed")
            return False
    return True

def save_data(title: str, filename: str, text_id: str, credit: str):
    """Saves the generated video data to video_creation/data/videos.json

    Args:
        title (str): Title of the content
        filename (str): The finished video filename
        text_id (str): Unique identifier for the content
        credit (str): Background credit information
    """
    videos_file = "./video_creation/data/videos.json"

    # Create the file if it doesn't exist
    if not os.path.exists(videos_file):
        os.makedirs(os.path.dirname(videos_file), exist_ok=True)
        with open(videos_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)

    # Load existing data
    with open(videos_file, "r+", encoding="utf-8") as raw_vids:
        try:
            done_vids = json.load(raw_vids)
        except json.JSONDecodeError:
            done_vids = []  # Reset if file is empty or corrupt

        # Skip if already saved
        if text_id in [video["id"] for video in done_vids]:
            return

        payload = {
            "id": text_id,
            "time": str(int(time.time())),
            "background_credit": credit,
            "title": title,
            "filename": filename,
        }
        done_vids.append(payload)

        # Write back to file
        raw_vids.seek(0)
        json.dump(done_vids, raw_vids, ensure_ascii=False, indent=4)
        raw_vids.truncate()

