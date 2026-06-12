# AGENTS.md

> Instructions for AI coding agents working on this codebase.

## What This Is

A Python pipeline that extracts viral short clips from YouTube videos with AI-generated animated subtitles. Think "open-source Submagic" — Whisper for transcription, LLM for viral moment detection, FFmpeg for video processing.

## Quick Start

```bash
pip install -r requirements.txt

# Web UI
python app.py  # Flask server at http://localhost:5000

# CLI
python main.py --url "https://youtube.com/watch?v=VIDEO_ID" --clips 3 --subtitle-style "TikTok Style"
```

**Required:** FFmpeg in PATH. An AI provider — Ollama (local/free), OpenAI, or Anthropic.

## Architecture

Linear pipeline, each step feeds the next:

```
YouTube URL → Download → Transcribe → Analyze → Extract Clips → Add Subtitles
```

### Modules (`modules/`)

| Module | Class | Purpose |
|--------|-------|---------|
| `downloader.py` | `YouTubeDownloader` | Downloads via yt-dlp. Returns `{filepath, title, duration}` |
| `transcriber.py` | `VideoTranscriber` | Whisper transcription with word-level timestamps |
| `analyzer.py` | `ViralMomentAnalyzer` | LLM scores transcript chunks for viral potential (0-10) |
| `video_processor.py` | `VideoProcessor` | FFmpeg clip extraction, horizontal/vertical formats, vertical layouts (`center-crop`, `split-stack`) |
| `subtitle_generator.py` | `SubtitleGenerator` | Word-by-word animated subtitles with style templates; karaoke active-word highlight when a template defines `highlight_color` |

### Entry Points

- **`app.py`** — Flask backend, SSE progress streaming, serves `templates/index.html`
- **`main.py`** — CLI with argparse (`--url`, `--clips`, `--quality`, `--subtitle-style`, `--provider`, etc.)
- **`config.py`** — All constants: model settings, clip lengths, subtitle templates, analysis params

### API Routes (`app.py`)

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/` | Web UI |
| `GET` | `/api/subtitle-styles` | List available styles |
| `GET` | `/api/downloads` | List downloaded videos |
| `GET` | `/api/clips/<filename>` | Serve a clip file |
| `POST` | `/api/upload` | Upload local video |
| `POST` | `/api/process` | Run full pipeline (SSE) |
| `POST` | `/api/restyle` | Re-apply subtitles with different style |

### Utilities (`utils/`)

- `helpers.py` — Shared helper functions
- `translations.py` — EN/FR UI translations
- `video_metadata.py` — Video file metadata extraction

## Key Configuration (`config.py`)

- `AI_PROVIDER`: `"ollama"` | `"openai"` | `"anthropic"`
- `WHISPER_MODEL`: `"base"` | `"small"` | `"medium"` | `"large-v3"` | `"large-v3-turbo"` (default; smaller models give poor non-English subtitles). CLI overrides: `--whisper-model`, `--language fr`
- `WHISPER_BACKEND`: `"faster-whisper"` | `"openai-whisper"`
- `MIN_VIRAL_SCORE`: Float 0-10, threshold for clip selection (default: 6.0)
- `MIN_CLIP_LENGTH` / `MAX_CLIP_LENGTH`: Clip duration bounds in seconds (15-60)
- `SUBTITLE_TEMPLATES`: Dict of named styles (Classic, Bold Yellow, TikTok Style, Neon, etc.)
- `CHUNK_STRATEGY`: `"sliding"` | `"smart"` | `"semantic"` | `"fixed"`

## Conventions

- **Output format:** Vertical 9:16 by default (TikTok/Reels/Shorts)
- **Vertical layouts:** `center-crop` (default, single speaker) or `split-stack` (two side-by-side speakers cropped and stacked vertically — use for two-person podcast sources). CLI: `--layout split-stack`
- **Viral subtitles:** the "Viral Highlight" template renders karaoke-style captions where the actively spoken word is colored and scaled. Any template gains this by defining `highlight_color` (and optional `highlight_scale`) in `config.py`
- **Working directories:** `downloads/`, `outputs/`, `transcripts/` — auto-created, gitignored
- **API keys:** Via `.env` file or environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- **Frontend:** Single-file HTML/CSS/JS in `templates/index.html`
- **Tests:** pytest suite in `tests/` — run `python -m pytest tests/ -q`

## Programmatic Usage

```python
from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor
from modules.subtitle_generator import SubtitleGenerator

downloader = YouTubeDownloader()
video = downloader.download("https://youtube.com/watch?v=...", "720p")

transcriber = VideoTranscriber()
transcript = transcriber.transcribe(video['filepath'])

analyzer = ViralMomentAnalyzer(provider="ollama")
moments = analyzer.analyze_transcript(transcript)

processor = VideoProcessor()
clips = processor.extract_multiple_clips(video['filepath'], moments[:3])

subtitler = SubtitleGenerator()
for clip, moment in zip(clips, moments[:3]):
    subtitler.add_subtitles(clip, transcript, moment['start'], moment['end'],
                            style_template="TikTok Style")
```
