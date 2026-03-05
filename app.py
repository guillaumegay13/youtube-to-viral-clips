import json
import queue
import threading
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, request, jsonify, Response, send_from_directory

from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor
from modules.subtitle_generator import SubtitleGenerator
from utils.helpers import check_dependencies, clean_filename
from config import (
    SUBTITLE_TEMPLATES, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    DOWNLOADS_DIR, OUTPUTS_DIR, SUPPORTED_FORMATS, CHUNK_DURATION,
)

app = Flask(__name__)

# In-memory session storage for restyle feature
_sessions: dict = {}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/subtitle-styles", methods=["GET"])
def subtitle_styles():
    styles = {name: tmpl["description"] for name, tmpl in SUBTITLE_TEMPLATES.items()}
    return jsonify(styles)


@app.route("/api/downloads", methods=["GET"])
def list_downloads():
    downloads_path = Path(DOWNLOADS_DIR)
    downloads_path.mkdir(exist_ok=True)
    files = [
        f.name for f in downloads_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    ]
    return jsonify(files)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    downloads_path = Path(DOWNLOADS_DIR)
    downloads_path.mkdir(exist_ok=True)
    filename = clean_filename(file.filename)
    save_path = downloads_path / filename
    file.save(str(save_path))
    return jsonify({"filename": filename})


@app.route("/api/clips/<path:filename>")
def serve_clip(filename):
    return send_from_directory(str(OUTPUTS_DIR), filename)


@app.route("/api/process", methods=["POST"])
def process_video():
    """Run the full pipeline and stream progress via SSE."""
    payload = request.get_json(silent=True) or {}

    source = payload.get("source", "youtube")
    url = payload.get("url", "")
    local_file = payload.get("local_file", "")
    quality = payload.get("quality", "best")
    ai_provider = payload.get("provider", "ollama")
    min_score = float(payload.get("min_score", 7.0))
    vertical_format = payload.get("vertical_format", True)
    add_subtitles = payload.get("add_subtitles", True)
    subtitle_style = payload.get("subtitle_style", "Submagic Yellow")

    # Validate inputs
    if source == "youtube" and not url:
        return jsonify({"error": "YouTube URL is required"}), 400
    if source == "local" and not local_file:
        return jsonify({"error": "Local file name is required"}), 400

    # Check API keys
    if ai_provider == "openai" and not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 400
    if ai_provider == "anthropic" and not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not set"}), 400

    # We use a queue so the background worker can push SSE messages
    q: queue.Queue = queue.Queue()

    def worker():
        try:
            # Step 1 — Acquire video
            if source == "youtube":
                q.put(("progress", {"step": 1, "total": 5, "message": "Downloading video from YouTube..."}))
                downloader = YouTubeDownloader()

                last_pct = [0]
                def _dl_progress(pct, downloaded, total):
                    # Throttle: only emit when percentage changes by >= 2 points
                    rounded = int(pct)
                    if rounded >= last_pct[0] + 2 or rounded >= 100:
                        last_pct[0] = rounded
                        q.put(("download_progress", {
                            "percent": min(rounded, 100),
                            "downloaded": downloaded,
                            "total": total,
                        }))

                video_data = downloader.download(url, quality, progress_callback=_dl_progress)
            else:
                q.put(("progress", {"step": 1, "total": 5, "message": "Loading local video..."}))
                save_path = Path(DOWNLOADS_DIR) / local_file
                if not save_path.exists():
                    q.put(("error", {"message": f"File not found: {local_file}"}))
                    return
                processor_probe = VideoProcessor()
                info = processor_probe.get_video_info(str(save_path))
                video_data = {
                    "video_id": None,
                    "title": save_path.stem,
                    "duration": info.get("duration", 0.0),
                    "description": "",
                    "upload_date": "",
                    "uploader": "Local",
                    "view_count": 0,
                    "like_count": 0,
                    "filepath": str(save_path),
                    "url": "Local file",
                }

            # Step 2 — Transcribe
            q.put(("progress", {"step": 2, "total": 5, "message": "Transcribing audio..."}))
            transcriber = VideoTranscriber()
            transcript = transcriber.transcribe(video_data["filepath"], language=None)
            detected_language = transcript.get("language", "en")

            # Step 3 — Analyze
            q.put(("progress", {"step": 3, "total": 5, "message": "Analyzing for viral moments..."}))
            analyzer = ViralMomentAnalyzer(provider=ai_provider)
            viral_moments = analyzer.analyze_transcript(transcript, chunk_duration=CHUNK_DURATION)

            if not viral_moments:
                q.put(("error", {"message": "No viral moments found. Try a different video or lower the minimum score."}))
                return

            high_viral_moments = [m for m in viral_moments if m["score"] >= min_score]
            if not high_viral_moments:
                high_viral_moments = viral_moments[:3]

            # Step 4 — Generate metadata (titles & descriptions)
            q.put(("progress", {"step": 4, "total": 5, "message": "Generating titles & descriptions..."}))
            processor = VideoProcessor()
            refined_moments = analyzer.refine_moments(high_viral_moments, transcript)
            analyzer.generate_clip_metadata(refined_moments, language=detected_language)
            validated_moments = processor.validate_timestamps(video_data["filepath"], refined_moments)

            # Step 5 — Extract clips
            q.put(("progress", {"step": 5, "total": 5, "message": f"Extracting {len(validated_moments)} clips..."}))

            progress_lock = threading.Lock()

            def extract_single_clip(index, moment):
                output_name = f"clip_{index+1}_score_{moment['score']:.1f}"
                pre_subtitle_path = processor.extract_clip(
                    video_data["filepath"],
                    moment["start"],
                    moment["end"],
                    output_name,
                    vertical_format=vertical_format,
                )
                clip_path = pre_subtitle_path
                if add_subtitles:
                    generator = SubtitleGenerator()
                    output_name = f"clip_{index+1}_final"
                    clip_path = generator.add_subtitles(
                        pre_subtitle_path,
                        transcript,
                        moment["start"],
                        moment["end"],
                        output_name,
                        vertical_format=vertical_format,
                        clip_start_time=moment["start"],
                        style_template=subtitle_style,
                        language=detected_language,
                    )
                return {
                    "index": index,
                    "path": clip_path,
                    "pre_subtitle_path": pre_subtitle_path,
                    "filename": Path(clip_path).name,
                    "start": moment["start"],
                    "end": moment["end"],
                    "score": moment["score"],
                    "duration": moment["duration"],
                    "reason": moment.get("reason", ""),
                    "title": moment.get("title", ""),
                    "description": moment.get("description", ""),
                }

            clips = []
            max_workers = min(4, len(validated_moments))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(extract_single_clip, i, m): i
                    for i, m in enumerate(validated_moments)
                }
                for future in as_completed(futures):
                    try:
                        clips.append(future.result())
                    except Exception as e:
                        q.put(("error", {"message": f"Failed to extract a clip: {str(e)}"}))

            clips.sort(key=lambda x: x["index"])
            # Remove internal index key
            for c in clips:
                c.pop("index", None)

            # Store session data for restyle feature
            session_id = str(uuid.uuid4())
            _sessions[session_id] = {
                "transcript": transcript,
                "clips": clips,
                "vertical_format": vertical_format,
                "language": detected_language,
            }

            # Build client-safe clip list (exclude internal paths)
            client_clips = [
                {k: v for k, v in c.items() if k not in ("path", "pre_subtitle_path")}
                for c in clips
            ]

            q.put(("done", {
                "title": video_data["title"],
                "clips": client_clips,
                "session_id": session_id,
            }))

        except Exception as e:
            q.put(("error", {"message": str(e)}))

    def generate():
        t = threading.Thread(target=worker, daemon=True)
        t.start()

        while True:
            try:
                event, data = q.get(timeout=30)
            except queue.Empty:
                # No message in 30s — send a keepalive comment so the
                # connection stays open, then keep waiting while the
                # worker thread is still alive.
                if t.is_alive():
                    yield ": keepalive\n\n"
                    continue
                # Worker died without sending done/error
                yield _sse("error", {"message": "Processing stopped unexpectedly"})
                break
            yield _sse(event, data)
            if event in ("done", "error"):
                break

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/restyle", methods=["POST"])
def restyle_clip():
    """Re-apply subtitles with a different style on an existing clip."""
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id", "")
    clip_index = payload.get("clip_index")
    style = payload.get("style", "Classic")

    if session_id not in _sessions:
        return jsonify({"error": "Session expired or not found"}), 404

    session = _sessions[session_id]
    clips = session["clips"]

    if clip_index is None or clip_index < 0 or clip_index >= len(clips):
        return jsonify({"error": "Invalid clip index"}), 400

    clip = clips[clip_index]
    pre_sub_path = clip.get("pre_subtitle_path", "")
    if not pre_sub_path or not Path(pre_sub_path).exists():
        return jsonify({"error": "Pre-subtitle clip not available"}), 404

    try:
        generator = SubtitleGenerator()
        output_name = f"clip_{clip_index+1}_restyle"
        new_path = generator.add_subtitles(
            pre_sub_path,
            session["transcript"],
            clip["start"],
            clip["end"],
            output_name,
            vertical_format=session["vertical_format"],
            clip_start_time=clip["start"],
            style_template=style,
            language=session["language"],
        )
        new_filename = Path(new_path).name
        # Update session data
        clip["path"] = new_path
        clip["filename"] = new_filename
        return jsonify({"filename": new_filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # use_reloader=False prevents watchdog from restarting the server
    # when temp files or downloads change on disk mid-processing.
    app.run(debug=True, use_reloader=False, port=5000)
