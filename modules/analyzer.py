import json
import ollama
from typing import List, Dict, Tuple
import re
from pathlib import Path

from config import LLM_MODEL, VIRAL_ANALYSIS_PROMPT, MIN_VIRAL_SCORE, MIN_CLIP_LENGTH, MAX_CLIP_LENGTH


class ViralMomentAnalyzer:
    def __init__(self, model_name: str = LLM_MODEL):
        self.model_name = model_name
        self._check_ollama_connection()
        
    def _check_ollama_connection(self):
        try:
            models = ollama.list()
            model_names = [model['name'] for model in models['models']]
            if self.model_name not in model_names and f"{self.model_name}:latest" not in model_names:
                print(f"Warning: Model '{self.model_name}' not found in Ollama.")
                print(f"Available models: {', '.join(model_names)}")
                print(f"Please run: ollama pull {self.model_name}")
        except Exception as e:
            print(f"Warning: Could not connect to Ollama: {e}")
            print("Make sure Ollama is running (ollama serve)")
    
    def analyze_transcript(self, transcript: Dict, chunk_duration: int = 45) -> List[Dict]:
        segments = transcript['segments']
        if not segments:
            return []
        
        chunks = self._create_chunks(segments, chunk_duration)
        
        print(f"Analyzing {len(chunks)} chunks for viral potential...")
        viral_moments = []
        
        for i, chunk in enumerate(chunks):
            print(f"Analyzing chunk {i+1}/{len(chunks)}...")
            
            score, reason = self._analyze_chunk(chunk['text'])
            
            if score >= MIN_VIRAL_SCORE:
                viral_moment = {
                    'start': chunk['start'],
                    'end': chunk['end'],
                    'duration': chunk['end'] - chunk['start'],
                    'score': score,
                    'reason': reason,
                    'text': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text']
                }
                viral_moments.append(viral_moment)
        
        viral_moments.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"Found {len(viral_moments)} potential viral moments")
        return viral_moments
    
    def _create_chunks(self, segments: List[Dict], chunk_duration: int) -> List[Dict]:
        chunks = []
        current_chunk = {
            'start': 0,
            'end': 0,
            'text': '',
            'segments': []
        }
        
        for segment in segments:
            if current_chunk['text'] and (segment['start'] - current_chunk['start']) >= chunk_duration:
                chunks.append(current_chunk.copy())
                current_chunk = {
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'segments': [segment]
                }
            else:
                if not current_chunk['text']:
                    current_chunk['start'] = segment['start']
                current_chunk['end'] = segment['end']
                current_chunk['text'] += ' ' + segment['text']
                current_chunk['segments'].append(segment)
        
        if current_chunk['text']:
            chunks.append(current_chunk)
        
        return chunks
    
    def _analyze_chunk(self, text: str) -> Tuple[float, str]:
        try:
            prompt = VIRAL_ANALYSIS_PROMPT.format(transcript=text)
            
            response = ollama.chat(
                model=self.model_name,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }]
            )
            
            response_text = response['message']['content']
            
            score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)', response_text, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.0
            score = min(10.0, max(0.0, score))  
            
            reason_match = re.search(r'Reason:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else "No specific reason provided"
            reason = reason.split('\n')[0][:200]  
            
            return score, reason
            
        except Exception as e:
            print(f"Error analyzing chunk: {e}")
            return 0.0, "Analysis failed"
    
    def refine_moments(self, moments: List[Dict], transcript: Dict) -> List[Dict]:
        refined_moments = []
        
        for moment in moments:
            # Store original times for subtitle alignment
            moment['original_start'] = moment['start']
            moment['original_end'] = moment['end']
            
            start_time = max(0, moment['start'] - 2)  
            end_time = min(transcript['duration'], moment['end'] + 2)
            
            duration = end_time - start_time
            if MIN_CLIP_LENGTH <= duration <= MAX_CLIP_LENGTH:
                moment['start'] = start_time
                moment['end'] = end_time
                moment['duration'] = duration
                refined_moments.append(moment)
            elif duration < MIN_CLIP_LENGTH:
                padding_needed = (MIN_CLIP_LENGTH - duration) / 2
                moment['start'] = max(0, start_time - padding_needed)
                moment['end'] = min(transcript['duration'], end_time + padding_needed)
                moment['duration'] = moment['end'] - moment['start']
                if moment['duration'] >= MIN_CLIP_LENGTH:
                    refined_moments.append(moment)
            else:
                center = (moment['original_start'] + moment['original_end']) / 2
                moment['start'] = center - MAX_CLIP_LENGTH / 2
                moment['end'] = center + MAX_CLIP_LENGTH / 2
                moment['duration'] = MAX_CLIP_LENGTH
                refined_moments.append(moment)
        
        return refined_moments


if __name__ == "__main__":
    print("Testing Viral Moment Analyzer...")
    
    sample_transcript = {
        'duration': 300,
        'segments': [
            {'start': 0, 'end': 5, 'text': 'Welcome to my video!'},
            {'start': 5, 'end': 10, 'text': 'Today we have something incredible to show you.'},
            {'start': 10, 'end': 15, 'text': 'You won\'t believe what happened next!'},
        ]
    }
    
    analyzer = ViralMomentAnalyzer()
    moments = analyzer.analyze_transcript(sample_transcript)
    
    for i, moment in enumerate(moments):
        print(f"\nMoment {i+1}:")
        print(f"  Time: {moment['start']:.1f}s - {moment['end']:.1f}s")
        print(f"  Score: {moment['score']}/10")
        print(f"  Reason: {moment['reason']}")