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

# AI Provider Settings
AI_PROVIDER = "ollama"  # Options: "ollama", "openai", "anthropic"
LLM_MODEL = "llama3.2:latest"  # For Ollama
OPENAI_MODEL = "gpt-4-turbo-preview"  # For OpenAI
ANTHROPIC_MODEL = "claude-3-opus-20240229"  # For Anthropic
AI_TEMPERATURE = 0.0  # Set to 0 for deterministic outputs

# API Keys (set via environment variables)
import os
from pathlib import Path

# Try to load from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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

# Subtitle style templates
SUBTITLE_TEMPLATES = {
    "Classic": {
        "description": "White text with black outline",
        "horizontal": {
            "fontsize": 80,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 4,
            "position": 0.85,
            "max_words": 3
        },
        "vertical": {
            "fontsize": 100,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 5,
            "position": 0.7,
            "max_words": 2
        }
    },
    "Bold Yellow": {
        "description": "Yellow text with thick black outline",
        "horizontal": {
            "fontsize": 85,
            "color": (255, 255, 0),
            "stroke_color": (0, 0, 0),
            "stroke_width": 6,
            "position": 0.85,
            "max_words": 3
        },
        "vertical": {
            "fontsize": 110,
            "color": (255, 255, 0),
            "stroke_color": (0, 0, 0),
            "stroke_width": 7,
            "position": 0.7,
            "max_words": 2
        }
    },
    "Minimal": {
        "description": "Small white text with thin outline",
        "horizontal": {
            "fontsize": 60,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 2,
            "position": 0.9,
            "max_words": 4
        },
        "vertical": {
            "fontsize": 80,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 3,
            "position": 0.8,
            "max_words": 3
        }
    },
    "TikTok Style": {
        "description": "Large white text with red/blue shadow",
        "horizontal": {
            "fontsize": 90,
            "color": (255, 255, 255),
            "stroke_color": (255, 0, 100),
            "stroke_width": 4,
            "position": 0.85,
            "max_words": 2
        },
        "vertical": {
            "fontsize": 120,
            "color": (255, 255, 255),
            "stroke_color": (255, 0, 100),
            "stroke_width": 5,
            "position": 0.8,
            "max_words": 2
        }
    },
    "Neon": {
        "description": "Cyan text with purple glow",
        "horizontal": {
            "fontsize": 85,
            "color": (0, 255, 255),
            "stroke_color": (128, 0, 255),
            "stroke_width": 5,
            "position": 0.85,
            "max_words": 3
        },
        "vertical": {
            "fontsize": 105,
            "color": (0, 255, 255),
            "stroke_color": (128, 0, 255),
            "stroke_width": 6,
            "position": 0.7,
            "max_words": 2
        }
    },
    "Ultra Bold": {
        "description": "Extra thick white text with heavy black outline",
        "horizontal": {
            "fontsize": 100,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 10,
            "position": 0.85,
            "max_words": 2
        },
        "vertical": {
            "fontsize": 140,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 12,
            "position": 0.8,
            "max_words": 2
        }
    },
    "Viral Bold": {
        "description": "Massive white text with extreme black outline",
        "horizontal": {
            "fontsize": 110,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 15,
            "position": 0.85,
            "max_words": 1
        },
        "vertical": {
            "fontsize": 160,
            "color": (255, 255, 255),
            "stroke_color": (0, 0, 0),
            "stroke_width": 18,
            "position": 0.8,
            "max_words": 1
        }
    }
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

# Analysis Settings
CHUNK_STRATEGY = "smart"  # Options: "smart", "sliding", "semantic", "fixed"
CHUNK_DURATION = 45  # For fixed strategy
SLIDING_WINDOW_SIZE = 60  # For sliding strategy
SLIDING_OVERLAP = 15  # For sliding strategy