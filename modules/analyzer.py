import json
import ollama
from typing import List, Dict, Tuple, Optional
import re
from pathlib import Path
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from config import (
    AI_PROVIDER, LLM_MODEL, OPENAI_MODEL, ANTHROPIC_MODEL,
    AI_TEMPERATURE, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    VIRAL_ANALYSIS_PROMPT, MIN_VIRAL_SCORE, MIN_CLIP_LENGTH, MAX_CLIP_LENGTH,
    CHUNK_STRATEGY, CHUNK_DURATION, SLIDING_WINDOW_SIZE, SLIDING_OVERLAP
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
    def __init__(self, provider: str = None, model_name: str = None, enable_cache: bool = True):
        self.provider = provider or AI_PROVIDER
        self.enable_cache = enable_cache

        # Set up cache directory
        self.cache_dir = Path(__file__).parent.parent / "cache" / "analysis"
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

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

    def _generate_cache_key(
        self,
        transcript: Dict,
        chunk_duration: int,
        strategy: str,
        threshold: float,
    ) -> str:
        """Generate a unique cache key based on transcript content and settings"""
        # Create a deterministic representation of the transcript
        cache_data = {
            'cache_schema_version': 2,
            'duration': transcript.get('duration', 0),
            'full_text': transcript.get('full_text', ''),
            'segments': [
                {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text']
                }
                for seg in transcript.get('segments', [])
            ],
            'strategy': strategy,
            'chunk_duration': chunk_duration,
            'default_chunk_duration': CHUNK_DURATION,
            'sliding_window_size': SLIDING_WINDOW_SIZE,
            'sliding_overlap': SLIDING_OVERLAP,
            'score_threshold': threshold,
            'min_viral_score': MIN_VIRAL_SCORE,
            'provider': self.provider,
            'model': self.model_name,
            'temperature': AI_TEMPERATURE
        }

        # Create hash of the data
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Load analysis results from cache if available"""
        if not self.enable_cache:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                print(f"✓ Loaded results from cache (key: {cache_key[:8]}...)")
                return cached_data
            except Exception as e:
                print(f"Warning: Failed to load cache: {e}")
                return None
        return None

    def _save_to_cache(self, cache_key: str, data: List[Dict]):
        """Save analysis results to cache"""
        if not self.enable_cache:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved results to cache (key: {cache_key[:8]}...)")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def analyze_transcript(self, transcript: Dict, chunk_duration: int = 30, strategy: str = None) -> List[Dict]:
        strategy = strategy or CHUNK_STRATEGY
        threshold = max(MIN_VIRAL_SCORE - 1.0, 4.0)

        # Check cache first
        cache_key = self._generate_cache_key(transcript, chunk_duration, strategy, threshold)
        cached_result = self._load_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        segments = transcript['segments']
        if not segments:
            return []

        if strategy == "sliding":
            chunks = self._create_sliding_chunks(segments)
        elif strategy == "smart":
            chunks = self._create_smart_chunks(segments, chunk_duration)
        else:  # "fixed" or unknown
            chunks = self._create_chunks(segments, chunk_duration)

        # Get language from transcript
        language = transcript.get('language', 'en')

        print(f"Analyzing {len(chunks)} chunks for viral potential...")
        viral_moments = []
        analyzed_chunks = []

        # Use parallel workers for API providers, sequential for local Ollama
        max_workers = 10 if self.provider in ("openai", "anthropic") else 1
        completed = [0]
        progress_lock = threading.Lock()

        def _analyze_one(chunk):
            score, reason = self._analyze_chunk(chunk['text'], language)
            with progress_lock:
                completed[0] += 1
                current = completed[0]
            print(f"Analyzed chunk {current}/{len(chunks)} (score: {score:.1f})")
            return chunk, score, reason

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_analyze_one, chunk) for chunk in chunks]
            for future in as_completed(futures):
                try:
                    chunk, score, reason = future.result()
                except Exception as e:
                    print(f"Error analyzing chunk: {e}")
                    continue

                analyzed_chunks.append({
                    'chunk': chunk,
                    'score': score,
                    'reason': reason,
                })

                # Filter: score must beat threshold (parse failures return 0.0, filtered out)
                if score >= threshold:
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

        # If no moments pass threshold, keep the top scored chunks anyway
        if not viral_moments and analyzed_chunks:
            print("No high-scoring moments found, selecting top chunks...")
            top_candidates = sorted(
                analyzed_chunks,
                key=lambda item: item['score'],
                reverse=True
            )[:3]

            for candidate in top_candidates:
                chunk = candidate['chunk']
                score = candidate['score']
                reason = candidate['reason'] or 'Selected as top content'
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

        # Save to cache before returning
        self._save_to_cache(cache_key, viral_moments)

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

    def _create_sliding_chunks(self, segments: List[Dict]) -> List[Dict]:
        """Create overlapping chunks using a sliding window for better coverage"""
        window = SLIDING_WINDOW_SIZE
        overlap = SLIDING_OVERLAP
        step = window - overlap

        if not segments:
            return []

        total_duration = segments[-1]['end']
        chunks = []
        window_start = 0.0

        while window_start < total_duration:
            window_end = window_start + window
            chunk_segments = [s for s in segments if s['end'] > window_start and s['start'] < window_end]
            if chunk_segments:
                chunks.append({
                    'start': chunk_segments[0]['start'],
                    'end': chunk_segments[-1]['end'],
                    'text': ' '.join(s['text'] for s in chunk_segments),
                    'segments': chunk_segments
                })
            window_start += step

        return chunks

    def _create_smart_chunks(self, segments: List[Dict], target_duration: int) -> List[Dict]:
        """Create chunks that break on natural sentence boundaries"""
        if not segments:
            return []

        target = max(1, int(target_duration))
        chunks = []
        current_chunk = {'start': 0, 'end': 0, 'text': '', 'segments': []}

        for seg in segments:
            if not current_chunk['text']:
                current_chunk['start'] = seg['start']

            current_chunk['end'] = seg['end']
            current_chunk['text'] += ' ' + seg['text']
            current_chunk['segments'].append(seg)

            duration = current_chunk['end'] - current_chunk['start']
            text = seg['text'].strip()

            # Split at sentence boundaries once we've reached the target duration
            if duration >= target and text and text[-1] in '.!?':
                chunks.append({
                    'start': current_chunk['start'],
                    'end': current_chunk['end'],
                    'text': current_chunk['text'].strip(),
                    'segments': list(current_chunk['segments'])
                })
                current_chunk = {'start': 0, 'end': 0, 'text': '', 'segments': []}

        if current_chunk['text']:
            chunks.append({
                'start': current_chunk['start'],
                'end': current_chunk['end'],
                'text': current_chunk['text'].strip(),
                'segments': list(current_chunk['segments'])
            })

        return chunks

    def _analyze_chunk(self, text: str, language: str = 'en') -> Tuple[float, str]:
        try:
            # Use structured prompt requesting JSON response
            if language == 'fr':
                structured_prompt = f"""Analyse ce segment de transcription pour détecter son POTENTIEL MAXIMAL D'ENGAGEMENT sur les réseaux sociaux.

Il s'agit d'un court extrait d'une longue vidéo YouTube. Évalue UNIQUEMENT ce segment pour son potentiel viral — ne prends pas en compte le contexte avant ou après.

Transcription :
{text}

Évalue les critères suivants de 0 à 10 (sois EXIGEANT — seuls les moments VRAIMENT viraux méritent plus de 7) :
- emotional_impact : choc, controverse, drame, indignation, excitation, admiration
- surprise_drama : révélation inattendue, rebondissement, conflit, information explosive
- quotability : phrase mémorable, réutilisable, parfaite pour un titre ou une légende
- hook_power : début captivant qui retient immédiatement l'attention

À PRIVILÉGIER : moments choquants, controverses, révélations, conflits, transformations spectaculaires, réactions extrêmes.
À ÉVITER : contenu générique, transitions, explications neutres, remplissage.

Réponds avec UNIQUEMENT du JSON valide dans ce format exact :
{{"emotional_impact": 0, "surprise_drama": 0, "quotability": 0, "hook_power": 0, "overall_score": 0, "moment_type": "...", "reason": "..."}}"""
            else:
                structured_prompt = f"""Analyze this transcript segment for MAXIMUM ENGAGEMENT potential on social media.

This is a short segment from a long YouTube video. Judge only THIS segment for viral potential — do not assume previous or following context.

Transcript:
{text}

Rate the following aspects from 0-10 (be STRICT — only TRULY viral moments deserve 7+):
- emotional_impact: shocking, controversial, dramatic, rage-inducing, excitement, awe
- surprise_drama: unexpected reveal, plot twist, explosive info, tension, conflict
- quotability: memorable, shareable, standalone lines for captions or titles
- hook_power: captivating start that demands attention, "wait what?", "no way!" moments

PRIORITIZE: shocking moments, controversies, reveals, conflicts, transformations, extreme reactions.
AVOID: generic content, flat explanations, transitions, filler.

Respond with ONLY valid JSON in this exact format:
{{"emotional_impact": 0, "surprise_drama": 0, "quotability": 0, "hook_power": 0, "overall_score": 0, "moment_type": "...", "reason": "..."}}"""

            if self.provider == "ollama":
                response_text = self._call_ollama(structured_prompt)
            elif self.provider == "openai":
                response_text = self._call_openai(structured_prompt)
            elif self.provider == "anthropic":
                response_text = self._call_anthropic(structured_prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            score = None
            reason = "High viral potential"

            # Try JSON parsing first
            try:
                parsed = self._extract_json(response_text)
                score = float(parsed.get('overall_score', 0))
                reason = parsed.get('reason', 'High viral potential')[:200]
            except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as parse_err:
                # Fall back to regex parsing
                # Debug: log first failure to help diagnose
                if not hasattr(self, '_parse_debug_logged'):
                    self._parse_debug_logged = True
                    print(f"[DEBUG] JSON parse failed ({parse_err}), raw response (first 500 chars):")
                    print(response_text[:500])
                    print("---")

                scores = {}
                aspect_patterns = {
                    'emotional_impact': [
                        r'emotional.?impact["\s:]+(\d+(?:\.\d+)?)',
                        r'Impact [ée]motionnel\s*:\s*(\d+(?:\.\d+)?)',
                    ],
                    'surprise_drama': [
                        r'surprise.?drama["\s:]+(\d+(?:\.\d+)?)',
                        r'Surprise\s*/?\s*(?:Drama|Tension)["\s:]+(\d+(?:\.\d+)?)',
                    ],
                    'quotability': [
                        r'quotability["\s:]+(\d+(?:\.\d+)?)',
                        r'Citabilit[ée]\s*:\s*(\d+(?:\.\d+)?)',
                    ],
                    'hook_power': [
                        r'hook.?power["\s:]+(\d+(?:\.\d+)?)',
                        r"Pouvoir d'accroche\s*:\s*(\d+(?:\.\d+)?)",
                    ],
                }
                for aspect, patterns in aspect_patterns.items():
                    for pattern in patterns:
                        match = re.search(pattern, response_text, re.IGNORECASE)
                        if match:
                            scores[aspect] = float(match.group(1))
                            break
                    else:
                        scores[aspect] = 0.0

                # Get overall score
                overall_patterns = [
                    r'overall.?score["\s:]+(\d+(?:\.\d+)?)',
                    r'Score global\s*:\s*(\d+(?:\.\d+)?)',
                    r'Overall:\s*(\d+(?:\.\d+)?)',
                    r'Score:\s*(\d+(?:\.\d+)?)'
                ]

                for pattern in overall_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        score = float(match.group(1))
                        break

                if score is None:
                    non_zero = [s for s in scores.values() if s > 0]
                    score = sum(non_zero) / len(non_zero) if non_zero else 0.0

                # Get reason
                reason_match = re.search(r'(?:reason|raison)["\s:=]+(.+)', response_text, re.IGNORECASE | re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip().strip('"').split('\n')[0][:200]

            score = min(10.0, max(0.0, score))
            return score, reason

        except Exception as e:
            print(f"Error analyzing chunk: {e}")
            return 0.0, "Analysis failed"
    
    def _extract_json(self, text: str) -> dict:
        """Robustly extract a JSON object from LLM output (handles thinking blocks, markdown, etc.)"""
        # Strip thinking/reasoning blocks that some models produce
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'<reasoning>.*?</reasoning>', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
        if md_match:
            return json.loads(md_match.group(1))

        # Find the last JSON object (models sometimes output explanation then JSON)
        # Use greedy match to handle nested content in string values
        json_matches = list(re.finditer(r'\{[^{}]*(?:"[^"]*"[^{}]*)*\}', cleaned, re.DOTALL))
        if json_matches:
            # Try each match from last to first (JSON is usually at the end)
            for m in reversed(json_matches):
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    continue

        # Last resort: find opening { and try to parse from there
        brace_idx = cleaned.rfind('{')
        if brace_idx >= 0:
            # Find matching closing brace
            depth = 0
            for i in range(brace_idx, len(cleaned)):
                if cleaned[i] == '{':
                    depth += 1
                elif cleaned[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return json.loads(cleaned[brace_idx:i+1])

        raise ValueError("No JSON object found in response")

    def _call_ollama(self, prompt: str) -> str:
        response = ollama.chat(
            model=self.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': AI_TEMPERATURE}
        )
        return response['message']['content']
    
    def _call_openai(self, prompt: str) -> str:
        kwargs = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_completion_tokens': 2000,
        }
        # Some models (e.g. gpt-5-mini) only support default temperature
        if AI_TEMPERATURE != 1.0:
            kwargs['temperature'] = AI_TEMPERATURE
        try:
            response = self.openai_client.chat.completions.create(**kwargs)
        except Exception as e:
            if 'temperature' in str(e):
                kwargs.pop('temperature', None)
                response = self.openai_client.chat.completions.create(**kwargs)
            else:
                raise
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
        """Find natural sentence boundaries for coherent clips with adaptive duration"""
        segments = transcript['segments']

        # Find segments that overlap with our time range
        relevant_segments = []
        for i, segment in enumerate(segments):
            if segment['end'] >= start_time - 8 and segment['start'] <= end_time + 8:
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
            if start_time - seg['start'] > 8:
                break

        # End: Look forward for sentence end indicators
        new_end = end_time
        # Track if we found a natural ending
        found_natural_end = False

        for i in range(end_segment_idx, len(relevant_segments)):
            idx, seg = relevant_segments[i]
            text = seg['text'].strip()

            # Calculate current duration
            current_duration = seg['end'] - new_start

            # Check if this segment ends a sentence/thought
            if self._is_sentence_end(text, idx, segments):
                # Only use this end if it creates a reasonable duration
                if MIN_CLIP_LENGTH <= current_duration <= MAX_CLIP_LENGTH:
                    new_end = seg['end']
                    found_natural_end = True
                    break
                elif current_duration < MIN_CLIP_LENGTH:
                    # Keep looking for a better end point
                    new_end = seg['end']
                    continue
                else:
                    # Too long, use this as a hard stop
                    new_end = seg['end']
                    found_natural_end = True
                    break

            # Hard limit: don't go more than MAX_CLIP_LENGTH from start
            if current_duration > MAX_CLIP_LENGTH:
                # Try to end at previous segment if it was a sentence boundary
                if i > end_segment_idx:
                    prev_idx, prev_seg = relevant_segments[i-1]
                    prev_text = prev_seg['text'].strip()
                    if self._is_sentence_end(prev_text, prev_idx, segments):
                        new_end = prev_seg['end']
                        found_natural_end = True
                break

        # Ensure we have reasonable boundaries
        final_start = max(0, new_start)
        final_end = min(transcript['duration'], new_end)

        # Snap to word boundaries to avoid cutting mid-word
        final_start = self._snap_to_word_boundary(transcript, final_start, 'start')
        final_end = self._snap_to_word_boundary(transcript, final_end, 'end')

        # Adaptive duration handling
        duration = final_end - final_start

        if duration < MIN_CLIP_LENGTH:
            # Only extend if we didn't find natural boundaries
            # Try to extend end first (more natural)
            needed = MIN_CLIP_LENGTH - duration
            end_extension = min(needed, transcript['duration'] - final_end)
            final_end += end_extension

            # If still too short, extend start
            duration = final_end - final_start
            if duration < MIN_CLIP_LENGTH:
                start_extension = MIN_CLIP_LENGTH - duration
                final_start = max(0, final_start - start_extension)

            # Re-snap after extension
            final_start = self._snap_to_word_boundary(transcript, final_start, 'start')
            final_end = self._snap_to_word_boundary(transcript, final_end, 'end')

        elif duration > MAX_CLIP_LENGTH:
            # If too long, trim to MAX_CLIP_LENGTH, preferring to keep the core moment
            # Keep more content after the start (where the viral moment likely is)
            excess = duration - MAX_CLIP_LENGTH
            # Trim 30% from start, 70% from end to keep the punch
            start_trim = excess * 0.3
            end_trim = excess * 0.7
            final_start += start_trim
            final_end -= end_trim

            # Re-snap after trimming
            final_start = self._snap_to_word_boundary(transcript, final_start, 'start')
            final_end = self._snap_to_word_boundary(transcript, final_end, 'end')

        # If we found a natural ending and the clip is within bounds, prefer it
        # even if it's not exactly at the boundaries
        if found_natural_end:
            duration = final_end - final_start
            # Allow clips slightly outside bounds if they have natural endings
            if MIN_CLIP_LENGTH * 0.8 <= duration <= MAX_CLIP_LENGTH * 1.1:
                # This is acceptable, keep the natural boundaries
                pass

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
        if not text:
            return False

        # Check for conjunctions that shouldn't end a clip (check FIRST to block)
        last_word = text.lower().split()[-1] if text else ''
        incomplete_endings = ['and', 'or', 'but', 'if', 'when', 'because', 'that', 'which',
                              'et', 'ou', 'mais', 'si', 'quand', 'parce', 'que', 'qui']
        if last_word in incomplete_endings:
            return False

        # Strong signal: ending punctuation
        if text[-1] in '.!?':
            return True

        # Check pauses to next segment
        if segment_idx < len(all_segments) - 1:
            pause = all_segments[segment_idx + 1]['start'] - all_segments[segment_idx]['end']
            next_text = all_segments[segment_idx + 1]['text'].strip()

            # Long pause (>0.8s) = natural break even without punctuation
            if pause > 0.8:
                return True

            # Next segment starts with uppercase + moderate pause = sentence boundary
            if next_text and next_text[0].isupper() and pause > 0.5:
                return True

            # Comma + pause > 0.6s = weak boundary (still usable)
            if text[-1] == ',' and pause > 0.6:
                return True

        return False
    
    def generate_clip_metadata(self, moments: List[Dict], language: str = 'en') -> List[Dict]:
        """Generate catchy titles and social media descriptions for each clip"""
        for moment in moments:
            excerpt = moment.get('context', moment.get('text', ''))[:500]
            reason = moment.get('reason', '')

            if language == 'fr':
                prompt = f"""Génère un titre accrocheur et une description pour les réseaux sociaux à partir de cet extrait vidéo.

Extrait : {excerpt}
Contexte : {reason}

Réponds avec UNIQUEMENT du JSON valide :
{{"title": "Titre accrocheur (max 80 caractères)", "description": "Description 2-3 phrases avec #hashtags pertinents"}}"""
            else:
                prompt = f"""Generate a catchy title and social media description for this video clip excerpt.

Excerpt: {excerpt}
Context: {reason}

Respond with ONLY valid JSON:
{{"title": "Catchy title (max 80 chars)", "description": "2-3 sentence description with relevant #hashtags"}}"""

            try:
                if self.provider == "ollama":
                    response_text = self._call_ollama(prompt)
                elif self.provider == "openai":
                    response_text = self._call_openai(prompt)
                elif self.provider == "anthropic":
                    response_text = self._call_anthropic(prompt)
                else:
                    raise ValueError(f"Unknown provider: {self.provider}")

                # Try JSON parsing
                try:
                    json_text = response_text.strip()
                    if '```' in json_text:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_text, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(1)
                    brace_match = re.search(r'\{[^{}]*\}', json_text, re.DOTALL)
                    if brace_match:
                        json_text = brace_match.group(0)
                    parsed = json.loads(json_text)
                    moment['title'] = parsed.get('title', reason[:80])[:80]
                    moment['description'] = parsed.get('description', reason)[:500]
                except (json.JSONDecodeError, ValueError, AttributeError):
                    moment['title'] = reason[:80] if reason else 'Viral Moment'
                    moment['description'] = reason or ''

            except Exception as e:
                print(f"Error generating metadata: {e}")
                moment['title'] = reason[:80] if reason else 'Viral Moment'
                moment['description'] = reason or ''

        return moments

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
