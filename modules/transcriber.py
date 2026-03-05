import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from tqdm import tqdm

from config import (
    TRANSCRIPTS_DIR,
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    WHISPER_TASK,
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    WHISPER_TEMPERATURE,
)


class VideoTranscriber:
    def __init__(self, model_name: str = WHISPER_MODEL):
        self.model_name = model_name
        self.model = None
        self.transcripts_dir = TRANSCRIPTS_DIR
        self.transcripts_dir.mkdir(exist_ok=True)

    def _cache_signature(self, language: Optional[str]) -> Dict[str, Any]:
        """Return cache signature for transcript compatibility checks."""
        return {
            'version': 2,
            'model': self.model_name,
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
        if self.model is None:
            # Load Whisper model
            
            # Suppress PyTorch warnings about torch.classes
            import warnings
            import logging
            
            # Also lower torch logging verbosity early
            logging.getLogger("torch").setLevel(logging.ERROR)
            
            # Temporarily suppress warnings during model loading
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*torch.classes.*")
                warnings.filterwarnings("ignore", message=".*Tried to instantiate class.*")
                warnings.filterwarnings("ignore", message=".*Examining the path of torch.classes.*")
                warnings.filterwarnings("ignore", message=".*pynvml package is deprecated.*")
                
                # Import whisper lazily so warning filters apply during import
                import whisper  # noqa: WPS433 (local import intentional)
                self.model = whisper.load_model(self.model_name)
            
            # Model loaded
    
    def transcribe(self, video_path: str, force: bool = False, language: str = None) -> Dict[str, Any]:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        transcript_path = self.transcripts_dir / f"{video_path.stem}_transcript.json"
        
        if transcript_path.exists() and not force:
            # Load existing transcript only if cache signature matches
            with open(transcript_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if self._is_compatible_cached_transcript(cached, language):
                return cached
        
        self._load_model()
        
        # Transcribe video
        
        try:
            # Use provided language or auto-detect
            whisper_language = language if language else WHISPER_LANGUAGE
            
            # IMPORTANT: Always use "transcribe" task to keep original language
            # Never use "translate" which would convert to English
            result = self.model.transcribe(
                str(video_path),
                language=whisper_language,
                task="transcribe",  # Force transcribe, not translate
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
            
            segments = []
            for segment in result['segments']:
                processed_segment = {
                    'id': segment['id'],
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'words': []
                }
                
                if 'words' in segment:
                    for word in segment['words']:
                        processed_segment['words'].append({
                            'word': word['word'].strip(),
                            'start': word['start'],
                            'end': word['end'],
                            'probability': word.get('probability', 1.0)
                        })
                
                segments.append(processed_segment)
            
            transcript_data = {
                'video_path': str(video_path),
                'language': result.get('language', 'unknown'),
                'duration': segments[-1]['end'] if segments else 0,
                'segments': segments,
                'full_text': result['text'].strip(),
                'transcriber': self._cache_signature(language),
            }
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            
            # Transcript saved
            
            return transcript_data
            
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
    
    def get_text_at_time(self, transcript: Dict, time: float) -> Optional[Dict]:
        for segment in transcript['segments']:
            if segment['start'] <= time <= segment['end']:
                for word in segment.get('words', []):
                    if word['start'] <= time <= word['end']:
                        return word
                return {
                    'word': segment['text'],
                    'start': segment['start'],
                    'end': segment['end']
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
        # Transcription complete
        pass
    except Exception as e:
        # Error occurred
        pass
