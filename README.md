# YouTube to Viral Clips

Submagic free open source alternative that can run with local AI model using Ollama and OpenAI Whisper (no API key needed).

## Overview

This tool downloads YouTube videos, transcribes them using OpenAI Whisper, analyzes the content for viral potential using AI (Ollama/OpenAI/Anthropic), and automatically extracts the most engaging clips with optional subtitles.

## Features

- Automatic viral moment detection with customizable scoring threshold
- Multi-language support (transcription and subtitles)
- Parallel clip extraction for faster processing
- Multiple AI providers: Ollama (local), OpenAI, Anthropic
- Customizable subtitle styles optimized for social media
- Vertical format option for TikTok/Reels/Shorts
- Clean, minimal web interface

## Requirements

- Python 3.8+
- FFmpeg
- Ollama (for local AI) or API keys for OpenAI/Anthropic

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/youtube-to-viral-clips.git
cd youtube-to-viral-clips
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

4. Set up AI provider:

For Ollama (local, free):
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2

# Start Ollama server
ollama serve
```

For OpenAI:
```bash
export OPENAI_API_KEY="your-api-key"
```

For Anthropic:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Web Interface

Run the Streamlit app:
```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Command Line

For direct Python usage:
```python
from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor

# Download video
downloader = YouTubeDownloader()
video_data = downloader.download("https://youtube.com/watch?v=...", "720p")

# Transcribe
transcriber = VideoTranscriber()
transcript = transcriber.transcribe(video_data['filepath'])

# Analyze for viral moments
analyzer = ViralMomentAnalyzer(provider="ollama")
viral_moments = analyzer.analyze_transcript(transcript)

# Extract clips
processor = VideoProcessor()
for moment in viral_moments[:3]:
    processor.extract_clip(
        video_data['filepath'],
        moment['start'],
        moment['end'],
        f"clip_score_{moment['score']:.1f}"
    )
```

## Configuration

Edit `config.py` to customize:

- `AI_PROVIDER`: Choose between "ollama", "openai", or "anthropic"
- `MIN_VIRAL_SCORE`: Minimum score threshold (0-10)
- `MIN_CLIP_LENGTH`: Minimum clip duration in seconds
- `MAX_CLIP_LENGTH`: Maximum clip duration in seconds
- `WHISPER_MODEL`: Whisper model size ("base", "small", "medium", "large")

## Subtitle Styles

Available subtitle templates:
- Classic: White text with black outline
- Bold Yellow: Yellow text with thick black outline
- Minimal: Small white text with thin outline
- TikTok Style: Large white text with colored shadow
- Neon: Cyan text with purple glow
- Ultra Bold: Extra thick white text
- Viral Bold: Massive white text for maximum impact

## Output

Clips are saved to the `outputs/` directory with the following naming:
- `clip_1_score_8.5.mp4` (without subtitles)
- `clip_1_final.mp4` (with subtitles)

## API Keys

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## Troubleshooting

### "Missing dependencies" error
Ensure FFmpeg is installed and accessible in your PATH.

### "Ollama connection failed"
Start the Ollama server with `ollama serve`.

### "No viral moments found"
Try lowering the minimum score threshold or using a different video.

### Subtitle language issues
The tool automatically detects the video language. Ensure Whisper's transcription task is set to "transcribe" (not "translate") in config.py.

## License

MIT License

## Contributing

Pull requests welcome. For major changes, please open an issue first.