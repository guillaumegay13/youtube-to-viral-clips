# YouTube Video Viral Moment Extractor

Automatically extract viral moments from YouTube videos and create short clips with animated subtitles using AI.

## Features

- 🎥 Download YouTube videos automatically
- 🎧 Transcribe audio using OpenAI Whisper (locally)
- 🤖 Analyze transcript for viral potential using local LLM (Ollama)
- ✂️ Extract clips with configurable duration (15-60 seconds)
- 🎨 Add word-by-word animated subtitles
- 📊 Generate summary reports

## Prerequisites

1. **Python 3.8+**
2. **FFmpeg** - [Download here](https://ffmpeg.org/download.html)
3. **Ollama** - [Install from here](https://ollama.ai/)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd youtube-viral-extractor
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install and setup Ollama:
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the LLM model
ollama pull llama2

# Start Ollama service
ollama serve
```

## Usage

### Basic Usage

Extract viral moments from a YouTube video:
```bash
python main.py --url "https://youtube.com/watch?v=VIDEO_ID"
```

### Advanced Options

```bash
# Specify video quality and number of clips
python main.py --url "https://youtube.com/watch?v=..." --quality 1080p --clips 3

# Skip subtitle generation
python main.py --url "https://youtube.com/watch?v=..." --no-subtitles

# Use local video file
python main.py --file "path/to/video.mp4" --clips 5

# Force re-transcription
python main.py --url "https://youtube.com/watch?v=..." --force-transcribe
```

### Command Line Arguments

- `--url`: YouTube video URL
- `--file`: Local video file path (alternative to URL)
- `--quality`: Video download quality (360p/480p/720p/1080p, default: 720p)
- `--clips`: Maximum number of clips to generate (default: 5)
- `--no-subtitles`: Skip adding subtitles to clips
- `--force-transcribe`: Force re-transcription even if transcript exists
- `--output-dir`: Custom output directory for clips

## Project Structure

```
youtube-viral-extractor/
├── main.py                 # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── modules/
│   ├── downloader.py      # YouTube video downloader
│   ├── transcriber.py     # Whisper transcription module
│   ├── analyzer.py        # Viral moment analysis
│   ├── video_processor.py # Video clip extraction
│   └── subtitle_generator.py # Subtitle generation
├── utils/
│   └── helpers.py         # Utility functions
├── downloads/             # Downloaded videos
├── outputs/              # Generated clips
└── transcripts/          # Saved transcripts
```

## Configuration

Edit `config.py` to customize:

- Video quality and clip duration limits
- Whisper model size (base/small/medium/large)
- LLM model for analysis
- Subtitle styling
- Viral score thresholds

## How It Works

1. **Download**: The app downloads the YouTube video in your specified quality
2. **Transcribe**: Whisper generates a word-level transcript with timestamps
3. **Analyze**: The local LLM analyzes transcript chunks for viral potential
4. **Extract**: FFmpeg extracts clips based on high-scoring moments
5. **Subtitle**: MoviePy adds animated word-by-word subtitles
6. **Output**: Final clips are saved with metadata and summary report

## Troubleshooting

### FFmpeg not found
- Ensure FFmpeg is installed and in your PATH
- Test with: `ffmpeg -version`

### Ollama connection error
- Make sure Ollama is running: `ollama serve`
- Check if model is installed: `ollama list`

### Whisper model download
- First run will download the Whisper model (~140MB for base)
- Ensure you have sufficient disk space

### Memory issues
- For long videos, consider using smaller Whisper models
- Close other applications to free up RAM

## Performance Tips

- Use GPU acceleration if available (CUDA for NVIDIA)
- Start with "base" Whisper model for faster processing
- Process shorter videos (<30 min) for best results
- Run on videos with clear speech for better transcription

## License

This project is provided as-is for educational purposes. Ensure you have the right to download and process any videos you use with this tool.