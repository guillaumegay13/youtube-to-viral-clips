import json
import ollama
from typing import List, Dict, Tuple, Optional
import re
from pathlib import Path
import os

from config import (
    AI_PROVIDER, LLM_MODEL, OPENAI_MODEL, ANTHROPIC_MODEL,
    AI_TEMPERATURE, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    VIRAL_ANALYSIS_PROMPT, MIN_VIRAL_SCORE, MIN_CLIP_LENGTH, MAX_CLIP_LENGTH
)

# Import API libraries only if needed
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None


class ViralMomentAnalyzer:
    def __init__(self, provider: str = None, model_name: str = None):
        self.provider = provider or AI_PROVIDER
        
        # Set model based on provider
        if self.provider == "ollama":
            self.model_name = model_name or LLM_MODEL
            self._check_ollama_connection()
        elif self.provider == "openai":
            self.model_name = model_name or OPENAI_MODEL
            self._check_openai_setup()
        elif self.provider == "anthropic":
            self.model_name = model_name or ANTHROPIC_MODEL
            self._check_anthropic_setup()
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")
        
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
    
    def _check_openai_setup(self):
        if not openai:
            raise Exception("OpenAI library not installed. Run: pip install openai")
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY environment variable not set")
        # Set up OpenAI client
        from openai import OpenAI
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    def _check_anthropic_setup(self):
        if not anthropic:
            raise Exception("Anthropic library not installed. Run: pip install anthropic")
        if not ANTHROPIC_API_KEY:
            raise Exception("ANTHROPIC_API_KEY environment variable not set")
        self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def analyze_transcript(self, transcript: Dict, chunk_duration: int = 30) -> List[Dict]:
        segments = transcript['segments']
        if not segments:
            return []
        
        chunks = self._create_chunks(segments, chunk_duration)
        
        # Get language from transcript
        language = transcript.get('language', 'en')
        
        print(f"Analyzing {len(chunks)} chunks for viral potential...")
        viral_moments = []
        
        for i, chunk in enumerate(chunks):
            print(f"Analyzing chunk {i+1}/{len(chunks)}...")
            
            score, reason = self._analyze_chunk(chunk['text'], language)
            
            # Be more lenient with scoring - use MIN_VIRAL_SCORE - 1 to catch more moments
            if score >= max(MIN_VIRAL_SCORE - 1.0, 3.0):
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
        
        # If no moments found, take the top chunks anyway
        if not viral_moments and chunks:
            print("No high-scoring moments found, selecting top chunks...")
            for i, chunk in enumerate(chunks[:3]):  # Take top 3 chunks
                viral_moment = {
                    'start': chunk['start'],
                    'end': chunk['end'],
                    'duration': chunk['end'] - chunk['start'],
                    'score': 5.0,  # Give them a moderate score
                    'reason': 'Selected as top content',
                    'text': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text']
                }
                viral_moments.append(viral_moment)
        
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
    
    def _analyze_chunk(self, text: str, language: str = 'en') -> Tuple[float, str]:
        try:
            # Use structured prompt based on language
            if language == 'fr':
                structured_prompt = f"""Analysez ce segment de transcription pour son potentiel viral.

Transcription: {text}

Évaluez les aspects suivants de 0 à 10:
1. Humour (drôle, spirituel, intelligent): 
2. Émotion (touchant, inspirant, choquant):
3. Surprise (inattendu, rebondissement, révélation):
4. Citation (phrases mémorables, pertinentes):

Format exact des réponses:
Humor: [score]
Emotion: [score]
Surprise: [score]
Quotability: [score]
Overall Score: [score moyen]
Reason: [explication en une phrase]"""
            else:
                structured_prompt = f"""Analyze this transcript segment for viral potential.

Transcript: {text}

Rate the following aspects from 0-10:
1. Humor (funny, witty, clever): 
2. Emotion (touching, inspiring, shocking):
3. Surprise (unexpected, plot twist, revelation):
4. Quotability (memorable phrases, relatable):

Provide scores in this exact format:
Humor: [score]
Emotion: [score]
Surprise: [score]
Quotability: [score]
Overall Score: [average score]
Reason: [one sentence explanation]"""
                            
            if self.provider == "ollama":
                response_text = self._call_ollama(structured_prompt)
            elif self.provider == "openai":
                response_text = self._call_openai(structured_prompt)
            elif self.provider == "anthropic":
                response_text = self._call_anthropic(structured_prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            # Parse structured response with more flexible patterns
            scores = {}
            for aspect in ['Humor', 'Emotion', 'Surprise', 'Quotability']:
                # Try multiple patterns to find the score
                patterns = [
                    f'{aspect}:\\s*(\\d+(?:\\.\\d+)?)',
                    f'{aspect}.*?(\\d+(?:\\.\\d+)?)/10',
                    f'{aspect}.*?score.*?(\\d+(?:\\.\\d+)?)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        scores[aspect] = float(match.group(1))
                        break
                else:
                    scores[aspect] = 0.0
            
            # Get overall score with flexible patterns
            overall_patterns = [
                r'Overall Score:\s*(\d+(?:\.\d+)?)',
                r'Overall:\s*(\d+(?:\.\d+)?)',
                r'Total.*?:\s*(\d+(?:\.\d+)?)',
                r'Score:\s*(\d+(?:\.\d+)?)'
            ]
            
            score = None
            for pattern in overall_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    score = float(match.group(1))
                    break
            
            if score is None:
                # Calculate average if overall not found
                if any(scores.values()):  # If we have at least one score
                    score = sum(scores.values()) / len([s for s in scores.values() if s > 0])
                else:
                    # If no scores found at all, look for any number between 0-10
                    any_number = re.findall(r'\b([0-9]|10)(?:\.\d+)?\b', response_text)
                    if any_number:
                        score = float(any_number[0])
                    else:
                        score = 5.0  # Default to middle score
            
            score = min(10.0, max(0.0, score))
            
            # Get reason
            reason_match = re.search(r'Reason:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else "High viral potential"
            reason = reason.split('\n')[0][:200]
            
            return score, reason
            
        except Exception as e:
            print(f"Error analyzing chunk: {e}")
            # Return a moderate score instead of 0 to avoid filtering out everything
            return 5.0, "Analysis uncertain"
    
    def _call_ollama(self, prompt: str) -> str:
        response = ollama.chat(
            model=self.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': AI_TEMPERATURE}
        )
        return response['message']['content']
    
    def _call_openai(self, prompt: str) -> str:
        response = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=AI_TEMPERATURE,
            max_tokens=500
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        response = self.anthropic_client.messages.create(
            model=self.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=AI_TEMPERATURE,
            max_tokens=500
        )
        return response.content[0].text
    
    def refine_moments(self, moments: List[Dict], transcript: Dict) -> List[Dict]:
        """Refine moments to ensure complete sentences and coherent context"""
        refined_moments = []
        
        for moment in moments:
            # Store original times for subtitle alignment
            moment['original_start'] = moment['start']
            moment['original_end'] = moment['end']
            
            # Find complete sentences around the moment
            start_time, end_time = self._find_sentence_boundaries(
                transcript, 
                moment['start'], 
                moment['end']
            )
            
            # The _find_sentence_boundaries method already handles duration constraints
            moment['start'] = start_time
            moment['end'] = end_time
            moment['duration'] = end_time - start_time
            
            # Add context information for better understanding
            moment['context'] = self._get_clip_context(transcript, start_time, end_time)
            
            refined_moments.append(moment)
        
        return refined_moments
    
    def _snap_to_word_boundary(self, transcript: Dict, time: float, boundary_type: str) -> float:
        """Snap a time to the nearest word boundary to avoid cutting words"""
        best_time = time
        min_distance = float('inf')
        
        # Look through all segments
        for segment in transcript['segments']:
            # Check segment boundaries
            if boundary_type == 'start':
                # For start boundary, prefer word starts
                if 'words' in segment and segment['words']:
                    for word in segment['words']:
                        word_start = word['start']
                        distance = abs(word_start - time)
                        if distance < min_distance and distance < 0.5:  # Within 0.5 seconds
                            min_distance = distance
                            best_time = word_start
                else:
                    # Fallback to segment start
                    seg_start = segment['start']
                    distance = abs(seg_start - time)
                    if distance < min_distance and distance < 0.5:
                        min_distance = distance
                        best_time = seg_start
            else:
                # For end boundary, prefer word ends
                if 'words' in segment and segment['words']:
                    for word in segment['words']:
                        word_end = word['end']
                        distance = abs(word_end - time)
                        if distance < min_distance and distance < 0.5:  # Within 0.5 seconds
                            min_distance = distance
                            best_time = word_end
                else:
                    # Fallback to segment end
                    seg_end = segment['end']
                    distance = abs(seg_end - time)
                    if distance < min_distance and distance < 0.5:
                        min_distance = distance
                        best_time = seg_end
        
        return best_time
    
    def _find_sentence_boundaries(self, transcript: Dict, start_time: float, end_time: float) -> Tuple[float, float]:
        """Find natural sentence boundaries for coherent clips"""
        segments = transcript['segments']
        
        # Find segments that overlap with our time range
        relevant_segments = []
        for i, segment in enumerate(segments):
            if segment['end'] >= start_time - 5 and segment['start'] <= end_time + 5:
                relevant_segments.append((i, segment))
        
        if not relevant_segments:
            return start_time, end_time
        
        # Find the segment containing the start time
        start_segment_idx = None
        for i, (idx, seg) in enumerate(relevant_segments):
            if seg['start'] <= start_time <= seg['end']:
                start_segment_idx = i
                break
        
        # Find the segment containing the end time
        end_segment_idx = None
        for i, (idx, seg) in enumerate(relevant_segments):
            if seg['start'] <= end_time <= seg['end']:
                end_segment_idx = i
                break
        
        # If we didn't find exact segments, use the closest ones
        if start_segment_idx is None:
            start_segment_idx = 0
        if end_segment_idx is None:
            end_segment_idx = len(relevant_segments) - 1
        
        # Look for sentence boundaries
        # Start: Look backwards for sentence start indicators
        new_start = start_time
        for i in range(start_segment_idx, -1, -1):
            idx, seg = relevant_segments[i]
            text = seg['text'].strip()
            
            # Check if this segment starts a new sentence/thought
            if self._is_sentence_start(text, idx, segments):
                new_start = seg['start']
                break
            
            # Don't go too far back
            if start_time - seg['start'] > 10:
                break
        
        # End: Look forward for sentence end indicators
        new_end = end_time
        for i in range(end_segment_idx, len(relevant_segments)):
            idx, seg = relevant_segments[i]
            text = seg['text'].strip()
            
            # Check if this segment ends a sentence/thought
            if self._is_sentence_end(text, idx, segments):
                new_end = seg['end']
                break
            
            # Don't go too far forward
            if seg['end'] - end_time > 10:
                break
        
        # Ensure we have reasonable boundaries
        final_start = max(0, new_start)
        final_end = min(transcript['duration'], new_end)
        
        # If the clip would be too short or too long, use original boundaries with padding
        duration = final_end - final_start
        if duration < MIN_CLIP_LENGTH:
            # Add padding symmetrically
            padding = (MIN_CLIP_LENGTH - duration) / 2
            final_start = max(0, final_start - padding)
            final_end = min(transcript['duration'], final_end + padding)
        elif duration > MAX_CLIP_LENGTH:
            # Trim symmetrically
            trim = (duration - MAX_CLIP_LENGTH) / 2
            final_start += trim
            final_end -= trim
        
        return final_start, final_end
    
    def _is_sentence_start(self, text: str, segment_idx: int, all_segments: List[Dict]) -> bool:
        """Check if a segment starts a new sentence or thought"""
        text = text.strip()
        
        # Check for capital letter at start (new sentence)
        if text and text[0].isupper():
            # Check if previous segment ended with punctuation
            if segment_idx > 0:
                prev_text = all_segments[segment_idx - 1]['text'].strip()
                if prev_text and prev_text[-1] in '.!?':
                    return True
            else:
                # First segment is always a sentence start
                return True
        
        # Check for question words
        question_starters = ['who', 'what', 'when', 'where', 'why', 'how', 'qui', 'que', 'quand', 'où', 'pourquoi', 'comment']
        first_word = text.lower().split()[0] if text else ''
        if first_word in question_starters:
            return True
        
        # Check for transition words
        transitions = ['however', 'but', 'so', 'therefore', 'meanwhile', 'next', 'then', 
                      'mais', 'donc', 'alors', 'ensuite', 'puis', 'cependant']
        if first_word in transitions:
            return True
        
        return False
    
    def _is_sentence_end(self, text: str, segment_idx: int, all_segments: List[Dict]) -> bool:
        """Check if a segment ends a sentence or thought"""
        text = text.strip()
        
        # Check for ending punctuation
        if text and text[-1] in '.!?':
            return True
        
        # Check if next segment starts a new sentence
        if segment_idx < len(all_segments) - 1:
            next_text = all_segments[segment_idx + 1]['text'].strip()
            if next_text and next_text[0].isupper():
                # Check for significant pause
                pause = all_segments[segment_idx + 1]['start'] - all_segments[segment_idx]['end']
                if pause > 0.5:  # Half second pause usually indicates sentence end
                    return True
        
        # Check for conjunctions that shouldn't end a clip
        ending_words = text.lower().split()[-1] if text else ''
        incomplete_endings = ['and', 'or', 'but', 'if', 'when', 'et', 'ou', 'mais', 'si', 'quand']
        if ending_words in incomplete_endings:
            return False
        
        return False
    
    def _get_clip_context(self, transcript: Dict, start_time: float, end_time: float) -> str:
        """Get the full text content of a clip for context"""
        segments = transcript['segments']
        clip_text = []
        
        for segment in segments:
            # Include segments that overlap with our clip
            if segment['start'] < end_time and segment['end'] > start_time:
                clip_text.append(segment['text'].strip())
        
        return ' '.join(clip_text)


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