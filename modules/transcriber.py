import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from config import (
    TRANSCRIPTS_DIR,
    WHISPER_BACKEND,
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    WHISPER_TASK,
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    WHISPER_TEMPERATURE,
    WHISPER_VAD_FILTER,
)


class VideoTranscriber:
    def __init__(self, model_name: str = WHISPER_MODEL, backend: str = WHISPER_BACKEND):
        self.model_name = model_name
        self.backend = backend
        self.model = None
        self.transcripts_dir = TRANSCRIPTS_DIR
        self.transcripts_dir.mkdir(exist_ok=True)

    def _cache_signature(self, language: Optional[str]) -> Dict[str, Any]:
        """Return cache signature for transcript compatibility checks."""
        return {
            'version': 3,
            'backend': self.backend,
            'model': self.model_name,
            'device': WHISPER_DEVICE,
            'compute_type': WHISPER_COMPUTE_TYPE,
            'vad_filter': WHISPER_VAD_FILTER,
            'task': WHISPER_TASK,
            'beam_size': WHISPER_BEAM_SIZE,
            'best_of': WHISPER_BEST_OF,
            'temperature': list(WHISPER_TEMPERATURE),
            'language': language if language else "auto",
            'word_timestamps': True,
        }

    def _is_compatible_cached_transcript(self, transcript_data: Dict, language: Optional[str]) -> bool:
        """Check if cached transcript matches the current transcription settings."""
        signature = transcript_data.get('transcriber', {})
        return signature == self._cache_signature(language)

    def _load_model(self):
        if self.model is not None:
            return

        if self.backend == "faster-whisper":
            self._load_faster_whisper_model()
        elif self.backend == "openai-whisper":
            self._load_openai_whisper_model()
        else:
            raise ValueError(f"Unknown whisper backend: {self.backend}")

    def _load_faster_whisper_model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise Exception(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc

        self.model = WhisperModel(
            self.model_name,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    def _load_openai_whisper_model(self):
        import logging
        import warnings

        logging.getLogger("torch").setLevel(logging.ERROR)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*torch.classes.*")
            warnings.filterwarnings("ignore", message=".*Tried to instantiate class.*")
            warnings.filterwarnings("ignore", message=".*Examining the path of torch.classes.*")
            warnings.filterwarnings("ignore", message=".*pynvml package is deprecated.*")

            try:
                import whisper  # noqa: WPS433
            except ImportError as exc:
                raise Exception(
                    "openai-whisper is not installed. Run: pip install openai-whisper"
                ) from exc

            self.model = whisper.load_model(self.model_name)

    def transcribe(self, video_path: str, force: bool = False, language: str = None) -> Dict[str, Any]:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        transcript_path = self.transcripts_dir / f"{video_path.stem}_transcript.json"

        if transcript_path.exists() and not force:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if self._is_compatible_cached_transcript(cached, language):
                return cached

        self._load_model()

        try:
            whisper_language = language if language else WHISPER_LANGUAGE

            if self.backend == "faster-whisper":
                transcript_data = self._transcribe_with_faster_whisper(video_path, whisper_language)
            else:
                transcript_data = self._transcribe_with_openai_whisper(video_path, whisper_language)

            transcript_data['transcriber'] = self._cache_signature(language)

            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)

            return transcript_data

        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    def _transcribe_with_faster_whisper(self, video_path: Path, language: Optional[str]) -> Dict[str, Any]:
        segments, info = self.model.transcribe(
            str(video_path),
            language=language,
            task=WHISPER_TASK,
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            temperature=WHISPER_TEMPERATURE,
            word_timestamps=True,
            condition_on_previous_text=False,
            vad_filter=WHISPER_VAD_FILTER,
        )

        raw_segments = list(segments)
        processed_segments = self._serialize_faster_whisper_segments(raw_segments)

        return {
            'video_path': str(video_path),
            'language': getattr(info, 'language', 'unknown') or 'unknown',
            'duration': processed_segments[-1]['end'] if processed_segments else 0,
            'segments': processed_segments,
            'full_text': ' '.join(segment['text'] for segment in processed_segments).strip(),
        }

    def _transcribe_with_openai_whisper(self, video_path: Path, language: Optional[str]) -> Dict[str, Any]:
        result = self.model.transcribe(
            str(video_path),
            language=language,
            task=WHISPER_TASK,
            verbose=False,
            word_timestamps=True,
            fp16=False,
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            temperature=WHISPER_TEMPERATURE,
            condition_on_previous_text=False,
            no_speech_threshold=0.5,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )

        processed_segments = self._serialize_openai_whisper_segments(result.get('segments', []))

        return {
            'video_path': str(video_path),
            'language': result.get('language', 'unknown'),
            'duration': processed_segments[-1]['end'] if processed_segments else 0,
            'segments': processed_segments,
            'full_text': result.get('text', '').strip(),
        }

    def _serialize_faster_whisper_segments(self, segments: Iterable[Any]) -> List[Dict[str, Any]]:
        processed_segments = []

        for index, segment in enumerate(segments):
            processed_segment = {
                'id': getattr(segment, 'id', index),
                'start': self._to_float(getattr(segment, 'start', 0.0), default=0.0),
                'end': self._to_float(getattr(segment, 'end', 0.0), default=0.0),
                'text': (getattr(segment, 'text', '') or '').strip(),
                'words': [],
            }

            for word in getattr(segment, 'words', None) or []:
                processed_segment['words'].append({
                    'word': (getattr(word, 'word', '') or '').strip(),
                    'start': self._to_float(getattr(word, 'start', 0.0), default=0.0),
                    'end': self._to_float(getattr(word, 'end', 0.0), default=0.0),
                    'probability': self._to_float(getattr(word, 'probability', 1.0), default=1.0),
                })

            processed_segments.append(processed_segment)

        return processed_segments

    def _to_float(self, value: Any, default: float) -> float:
        if value is None:
            return default
        return float(value)

    def _serialize_openai_whisper_segments(self, segments: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed_segments = []

        for segment in segments:
            processed_segment = {
                'id': segment['id'],
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'].strip(),
                'words': [],
            }

            for word in segment.get('words', []):
                processed_segment['words'].append({
                    'word': word['word'].strip(),
                    'start': word['start'],
                    'end': word['end'],
                    'probability': word.get('probability', 1.0),
                })

            processed_segments.append(processed_segment)

        return processed_segments

    def get_text_at_time(self, transcript: Dict, time: float) -> Optional[Dict]:
        for segment in transcript['segments']:
            if segment['start'] <= time <= segment['end']:
                for word in segment.get('words', []):
                    if word['start'] <= time <= word['end']:
                        return word
                return {
                    'word': segment['text'],
                    'start': segment['start'],
                    'end': segment['end'],
                }
        return None

    def get_segments_in_range(self, transcript: Dict, start_time: float, end_time: float) -> List[Dict]:
        segments = []
        for segment in transcript['segments']:
            if segment['start'] < end_time and segment['end'] > start_time:
                segments.append(segment)
        return segments

    def get_words_in_range(self, transcript: Dict, start_time: float, end_time: float) -> List[Dict]:
        words = []
        segments = self.get_segments_in_range(transcript, start_time, end_time)

        for segment in segments:
            for word in segment.get('words', []):
                if word['start'] < end_time and word['end'] > start_time:
                    words.append(word)

        return words


if __name__ == "__main__":
    transcriber = VideoTranscriber()
    video_path = input("Enter video file path to test transcription: ")

    try:
        transcript = transcriber.transcribe(video_path)
        pass
    except Exception:
        pass
