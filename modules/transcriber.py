import json
import whisper
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from tqdm import tqdm

from config import TRANSCRIPTS_DIR, WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_TASK


class VideoTranscriber:
    def __init__(self, model_name: str = WHISPER_MODEL):
        self.model_name = model_name
        self.model = None
        self.transcripts_dir = TRANSCRIPTS_DIR
        self.transcripts_dir.mkdir(exist_ok=True)
        
    def _load_model(self):
        if self.model is None:
            # Load Whisper model
            
            # Suppress PyTorch warnings about torch.classes
            import warnings
            import logging
            
            # Temporarily suppress warnings during model loading
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*torch.classes.*")
                warnings.filterwarnings("ignore", message=".*Tried to instantiate class.*")
                warnings.filterwarnings("ignore", message=".*Examining the path of torch.classes.*")
                
                # Also suppress logging warnings
                logging.getLogger("torch").setLevel(logging.ERROR)
                
                self.model = whisper.load_model(self.model_name)
            
            # Model loaded
    
    def transcribe(self, video_path: str, force: bool = False, language: str = None) -> Dict[str, any]:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        transcript_path = self.transcripts_dir / f"{video_path.stem}_transcript.json"
        
        if transcript_path.exists() and not force:
            # Load existing transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
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
                fp16=False  
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
                'full_text': result['text'].strip()
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