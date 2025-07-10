import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUTS_DIR = BASE_DIR / "outputs"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

for dir_path in [DOWNLOADS_DIR, OUTPUTS_DIR, TRANSCRIPTS_DIR]:
    dir_path.mkdir(exist_ok=True)

VIDEO_QUALITY = "720p"
WHISPER_MODEL = "base"  
LLM_MODEL = "llama3.2:latest"  
MIN_CLIP_LENGTH = 15  
MAX_CLIP_LENGTH = 60  
CLIP_BUFFER_SECONDS = 2  

SUBTITLE_STYLE = {
    "font": "Arial-Bold",
    "fontsize": 80,
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 4,
    "position": ("center", 0.7),  
    "method": "caption"
}

VERTICAL_SUBTITLE_STYLE = {
    "font": "Arial-Bold",
    "fontsize": 100,
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 5,
    "position": ("center", 0.7),
    "method": "caption"
}

VIRAL_ANALYSIS_PROMPT = """Analyze this transcript segment for viral potential. 
Score from 0-10 based on: humor, emotion, surprisingness, quotability.
Provide a brief explanation of why this could go viral.

Transcript:
{transcript}

Response format:
Score: [0-10]
Reason: [Brief explanation]
"""

MAX_VIDEO_SIZE_MB = 500
SUPPORTED_FORMATS = [".mp4", ".webm", ".mkv"]
OUTPUT_FORMAT = "mp4"
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"

WHISPER_LANGUAGE = None  
WHISPER_TASK = "transcribe"  

DEFAULT_NUM_CLIPS = 5
MIN_VIRAL_SCORE = 6.0