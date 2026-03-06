import ffmpeg
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import os
import re

from config import SUBTITLE_STYLE, VERTICAL_SUBTITLE_STYLE, OUTPUTS_DIR, SUBTITLE_TEMPLATES
from modules.transcriber import VideoTranscriber
from utils.video_metadata import get_video_info


class SubtitleGenerator:
    # FFmpeg/libass on many systems fails to render modern color emojis.
    # We map them to symbol glyphs that reliably render in ASS subtitles.
    EMOJI_ASS_FALLBACKS = {
        "🔥": ("⚡", "Apple Symbols"),
        "💰": ("$", None),
        "😂": ("☺", "Apple Symbols"),
        "🤯": ("⚠", "Apple Symbols"),
        "💡": ("☀", "Apple Symbols"),
        "🚀": ("▶", "Apple Symbols"),
        "⚠": ("⚠", "Apple Symbols"),
        "⚡": ("⚡", "Apple Symbols"),
        "❤": ("♥", None),
        "🤔": ("☯", "Apple Symbols"),
        "✅": ("✔", "Zapf Dingbats"),
        "❌": ("✖", "Zapf Dingbats"),
    }

    def __init__(self, output_dir: Path = OUTPUTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.transcriber = VideoTranscriber()
        
    def add_subtitles(self, video_path: str, transcript: Dict,
                     start_time: float, end_time: float,
                     output_name: Optional[str] = None, vertical_format: bool = True,
                     clip_start_time: Optional[float] = None, style_template: str = "Classic",
                     language: str = "en") -> str:
        """Fast subtitle generation using FFmpeg subtitles filter"""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_name:
            output_filename = f"{output_name}_subtitled.mp4"
        else:
            output_filename = f"{video_path.stem}_subtitled.mp4"

        output_path = self.output_dir / output_filename

        try:
            # Reuse cached probe metadata so each clip render does not reprobe the file.
            video_info = get_video_info(str(video_path))
            duration = float(video_info.get('duration', 0.0))
            video_width = int(video_info.get('width', 1080))
            video_height = int(video_info.get('height', 1920))
            
            # Get subtitle style from template
            if style_template in SUBTITLE_TEMPLATES:
                template = SUBTITLE_TEMPLATES[style_template]
                style_settings = template['vertical'] if vertical_format else template['horizontal']
            else:
                # Fallback to default styles
                style = VERTICAL_SUBTITLE_STYLE if vertical_format else SUBTITLE_STYLE
                style_settings = {
                    'fontsize': style['fontsize'],
                    'color': 'white' if style['color'] == 'white' else 'black',
                    'stroke_color': 'black' if style['stroke_color'] == 'black' else 'white',
                    'stroke_width': style['stroke_width'],
                    'position': style['position'][1] if isinstance(style['position'], tuple) else style['position']
                }
            
            # If clip_start_time is provided, use it as the offset
            if clip_start_time is not None:
                video_offset = clip_start_time
            else:
                video_offset = start_time
            
            # Get words for the entire clip duration
            words = self.transcriber.get_words_in_range(
                transcript, 
                video_offset, 
                video_offset + duration
            )
            
            # Use transcript's detected language if available
            actual_language = transcript.get('language', language)
            
            # Group words intelligently
            max_words = style_settings.get('max_words', 3)
            word_groups = self._group_words(words, max_words, actual_language)

            # Optional Submagic-like smart emojis
            if style_settings.get('smart_emojis', False):
                emoji_density = float(style_settings.get('emoji_density', 0.4))
                word_groups = self._add_smart_emojis(
                    word_groups,
                    language=actual_language,
                    density=emoji_density,
                )
            
            # Create subtitle file in ASS format
            ass_file = self._create_ass_file(word_groups, style_settings, video_offset,
                                             video_width=video_width, video_height=video_height)
            
            # Use FFmpeg with subtitles filter
            input_stream = ffmpeg.input(str(video_path))
            
            # Split into video and audio streams
            video = input_stream.video
            audio = input_stream.audio
            
            # Apply subtitles filter only to video stream
            video = video.filter('ass', ass_file)
            
            # Output with both video and audio streams
            stream = ffmpeg.output(
                video,
                audio,
                str(output_path),
                vcodec='h264',  # Use h264 for better compatibility
                acodec='copy',  # Copy audio without re-encoding (faster)
                preset='veryfast',  # Much faster encoding
                crf=23,
                movflags='faststart'  # For better streaming
            )
            
            # Run FFmpeg
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # Clean up temporary file
            os.unlink(ass_file)
            
            return str(output_path)
            
        except Exception as e:
            # Clean up on error
            if 'ass_file' in locals() and os.path.exists(ass_file):
                os.unlink(ass_file)
            raise Exception(f"Error adding subtitles: {str(e)}")
    
    def _create_ass_file(self, word_groups: List[Dict], style_settings: Dict, video_offset: float,
                         video_width: int = 1080, video_height: int = 1920) -> str:
        """Create ASS subtitle file with styling"""
        # Create temporary ASS file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8')

        # With PlayResY matching the video, font sizes are in video pixels directly.
        # Scale proportionally if video isn't 1920px tall.
        fontsize = max(10, int(style_settings['fontsize'] * video_height / 1920))
        primary_color = self._color_to_ass(style_settings['color'])
        outline_color = self._color_to_ass(style_settings['stroke_color'])
        # Scale outline width proportionally to font size
        outline_width = max(1, int(style_settings['stroke_width'] * 0.3))

        # Proportional margins based on resolution
        margin_lr = max(10, int(video_width * 0.03))   # 3% of width
        min_margin_v = int(video_height * 0.05)          # 5% of height

        # Position: 2 = bottom center, 8 = top center, 5 = middle center
        # y_pos is a ratio (0=top, 1=bottom); margin_v is in PlayRes pixels
        y_pos = style_settings['position']
        if y_pos < 0.3:  # Top
            alignment = 8
            margin_v = max(min_margin_v, int(y_pos * video_height))
        elif y_pos >= 0.6:  # Bottom
            alignment = 2
            margin_v = max(min_margin_v, int((1 - y_pos) * video_height))
        else:  # Middle
            alignment = 5
            margin_v = max(min_margin_v, int(video_height * 0.1))

        # Write ASS header
        temp_file.write("[Script Info]\n")
        temp_file.write("Title: Generated Subtitles\n")
        temp_file.write("ScriptType: v4.00+\n")
        temp_file.write("Collisions: Normal\n")
        temp_file.write("PlayDepth: 0\n")
        temp_file.write("Timer: 100.0000\n")
        temp_file.write(f"PlayResX: {video_width}\n")
        temp_file.write(f"PlayResY: {video_height}\n")
        temp_file.write("WrapStyle: 1\n\n")

        temp_file.write("[V4+ Styles]\n")
        temp_file.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, ")
        temp_file.write("OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ")
        temp_file.write("ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, ")
        temp_file.write("Alignment, MarginL, MarginR, MarginV, Encoding\n")

        # Bold font for better visibility
        font_name = style_settings.get('font', 'Arial')
        temp_file.write(f"Style: Default,{font_name},{fontsize},{primary_color},{primary_color},")
        temp_file.write(f"{outline_color},&H00000000,-1,0,0,0,100,100,0,0,1,{outline_width},0,")
        temp_file.write(f"{alignment},{margin_lr},{margin_lr},{margin_v},1\n\n")
        
        temp_file.write("[Events]\n")
        temp_file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        # Write subtitle events
        for group in word_groups:
            start_time = group['start'] - video_offset
            end_time = group['end'] - video_offset
            
            # Skip if outside clip bounds
            if start_time < 0 or end_time < 0:
                continue
                
            start_str = self._seconds_to_ass_time(start_time)
            end_str = self._seconds_to_ass_time(end_time)
            text = self._format_ass_text(group['text'])


            temp_file.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n")
        
        temp_file.close()
        return temp_file.name
    
    def _color_to_ass(self, color) -> str:
        """Convert color to ASS format (&HAABBGGRR)"""
        if isinstance(color, str):
            if color == 'white':
                return "&H00FFFFFF"
            elif color == 'black':
                return "&H00000000"
            elif color == 'yellow':
                return "&H0000FFFF"
            elif color == 'cyan':
                return "&H00FFFF00"
            else:
                return "&H00FFFFFF"
        elif isinstance(color, tuple) and len(color) == 3:
            # Convert RGB to BGR and format as ASS color
            r, g, b = color
            return f"&H00{b:02X}{g:02X}{r:02X}"
        else:
            return "&H00FFFFFF"

    def _sanitize_ass_text(self, text: str) -> str:
        """Remove ASS control characters and normalize spaces."""
        sanitized = text.replace('\\', '')
        sanitized = sanitized.replace('{', '(').replace('}', ')')
        return ' '.join(sanitized.split())

    def _normalize_emoji_key(self, text: str) -> str:
        """Normalize emoji variants (variation selectors, skin tones, ZWJ)."""
        # Strip common variation selector and zero-width joiner
        return text.replace('\ufe0f', '').replace('\u200d', '')

    def _to_ass_symbol(self, token: str) -> str:
        """Convert an emoji token into an ASS-safe symbol token with optional font override."""
        normalized = self._normalize_emoji_key(token.strip())

        if normalized in self.EMOJI_ASS_FALLBACKS:
            symbol, font_name = self.EMOJI_ASS_FALLBACKS[normalized]
            if font_name:
                return rf"{{\fn{font_name}}}{symbol}{{\r}}"
            return symbol

        return token

    def _format_ass_text(self, text: str) -> str:
        """Sanitize subtitle text and translate unsupported emojis to renderable symbols."""
        sanitized = self._sanitize_ass_text(text)
        if not sanitized:
            return sanitized

        tokens = sanitized.split()
        converted_tokens = [self._to_ass_symbol(token) for token in tokens]
        return ' '.join(converted_tokens)
    
    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format (h:mm:ss.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def _group_words(self, words: List[Dict], max_words: int = 3, language: str = "en") -> List[Dict]:
        """Group words intelligently for better readability"""
        if not words:
            return []
        
        # Common short words that should be grouped with the next word
        if language == "fr":
            # French short words
            short_words = {
                'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'à', 'au', 'aux',
                'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'que', 'qui', 'où',
                'ce', 'ces', 'cet', 'cette', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
                'son', 'sa', 'ses', 'notre', 'nos', 'votre', 'vos', 'leur', 'leurs',
                'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
                'me', 'te', 'se', 'ne', 'y', 'en', 'lui', 'leur',
                'est', 'sont', 'suis', 'es', 'êtes', 'sommes', 'ai', 'as', 'a',
                'ont', 'avons', 'avez', "j'ai", "c'est", "n'est", "qu'est",
                'd\'un', 'd\'une', 'l\'un', 'l\'une', 'jusqu\'à', 'qu\'il', 'qu\'elle'
            }
        else:
            # English short words
            short_words = {
                'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                'could', 'should', 'may', 'might', 'can', "can't", "don't",
                "won't", "isn't", "aren't", "wasn't", "weren't", "i'm", "you're",
                "he's", "she's", "it's", "we're", "they're", "i've", "you've",
                "we've", "they've", "i'll", "you'll", "he'll", "she'll", "we'll"
            }
        
        # Pre-merge apostrophe fragments (e.g. "l'" + "homme" → "l'homme")
        merged_words = []
        i = 0
        while i < len(words):
            w = dict(words[i])  # shallow copy
            clean = w['word'].strip()
            # If word ends with apostrophe and next word follows, merge them
            if clean.endswith("'") and i + 1 < len(words):
                nxt = words[i + 1]
                w['word'] = clean + nxt['word'].strip()
                w['end'] = nxt['end']
                merged_words.append(w)
                i += 2
                continue
            # If word is just an apostrophe or starts with one (e.g. "'homme")
            # and previous merged word ended with letter, merge back
            if clean.startswith("'") and merged_words:
                prev = merged_words[-1]
                prev['word'] = prev['word'].strip() + clean
                prev['end'] = w['end']
                i += 1
                continue
            merged_words.append(w)
            i += 1

        words = merged_words

        groups = []
        current_group = []
        current_start = None
        current_end = None

        for i, word in enumerate(words):
            word_text = word['word'].strip().lower()

            # Start a new group if needed
            if current_start is None:
                current_start = word['start']

            # Clean word text - remove backslashes and extra spaces
            clean_word = word['word'].strip().replace('\\', '')

            current_group.append(clean_word)
            current_end = word['end']

            # Decide if we should continue grouping
            should_continue = False

            # Check if current word is a short word that should stay with next
            if i < len(words) - 1:
                next_word = words[i + 1]
                time_gap = next_word['start'] - word['end']

                # Continue if:
                # 1. Current word is a short word
                # 2. Time gap is small (less than 0.3 seconds)
                # 3. Current group has less than max_words
                # 4. Total character count would be under 30
                if (word_text in short_words and time_gap < 0.3 and
                    len(current_group) < max_words):
                    should_continue = True
                elif (len(current_group) < max_words and time_gap < 0.2 and
                      len(' '.join(current_group + [next_word['word']])) < 30):
                    should_continue = True
            
            # Create group if we shouldn't continue or it's the last word
            if not should_continue or i == len(words) - 1:
                groups.append({
                    'text': ' '.join(current_group),
                    'start': current_start,
                    'end': current_end
                })
                current_group = []
                current_start = None
                current_end = None
        
        return groups

    def _add_smart_emojis(self, word_groups: List[Dict], language: str = "en", density: float = 0.4) -> List[Dict]:
        """Append context-aware emojis to a controlled subset of subtitle groups."""
        if not word_groups:
            return word_groups

        density = max(0.0, min(1.0, density))
        max_emoji_groups = int(len(word_groups) * density)
        if max_emoji_groups == 0 and density > 0:
            max_emoji_groups = 1

        enriched_groups = []
        used_emoji_groups = 0
        last_emoji = None

        for group in word_groups:
            enriched_group = dict(group)
            text = enriched_group.get('text', '').strip()

            if (
                used_emoji_groups >= max_emoji_groups
                or not text
                or self._contains_emoji(text)
                or len(text.split()) <= 1
            ):
                enriched_groups.append(enriched_group)
                continue

            emoji = self._pick_emoji_for_text(text, language, avoid_emoji=last_emoji)
            if emoji:
                enriched_group['text'] = f"{text} {emoji}"
                used_emoji_groups += 1
                last_emoji = emoji

            enriched_groups.append(enriched_group)

        return enriched_groups

    def _pick_emoji_for_text(self, text: str, language: str = "en", avoid_emoji: Optional[str] = None) -> Optional[str]:
        """Map subtitle text to an emoji using lightweight keyword rules."""
        normalized = re.sub(r"[^\w\s']", " ", text.lower(), flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = set(normalized.split())

        phrase_rules = [
            ("🤯", ["mind blown", "no way", "c est fou", "impossible"]),
            ("💡", ["pro tip", "top tip", "petit conseil", "astuce rapide"]),
            ("💰", ["make money", "earn money", "gagner de l argent"]),
        ]

        for emoji, phrases in phrase_rules:
            if avoid_emoji == emoji:
                continue
            if any(phrase in normalized for phrase in phrases):
                return emoji

        keyword_rules = [
            ("😂", {
                "funny", "joke", "hilarious", "laugh", "lol", "haha",
                "drôle", "blague", "mdr", "rire"
            }),
            ("🔥", {
                "viral", "insane", "crazy", "wild", "amazing", "epic", "best", "fire",
                "incroyable", "dingue", "ouf", "énorme"
            }),
            ("🤯", {
                "shocking", "unbelievable", "unexpected", "secret", "truth",
                "choquant", "hallucinant", "surprenant"
            }),
            ("💡", {
                "tip", "tips", "hack", "lesson", "learn", "advice", "strategy",
                "astuce", "conseil", "apprendre", "stratégie", "leçon"
            }),
            ("💰", {
                "money", "cash", "profit", "income", "revenue", "dollar", "million", "business",
                "argent", "revenu", "euros", "euro", "entreprise"
            }),
            ("🚀", {
                "grow", "growth", "scale", "launch", "boost", "explode", "success",
                "croissance", "lancer", "boost", "succès"
            }),
            ("⚠️", {
                "warning", "danger", "risk", "mistake", "avoid", "careful",
                "attention", "danger", "risque", "erreur", "évite", "evite"
            }),
            ("❤️", {
                "love", "heart", "beautiful", "amour", "aime", "coeur", "cœur"
            }),
            ("⚡", {
                "fast", "quick", "instant", "now", "today", "rapidement", "vite", "maintenant"
            }),
        ]

        for emoji, keywords in keyword_rules:
            if avoid_emoji == emoji:
                continue
            if tokens.intersection(keywords):
                return emoji

        if avoid_emoji != "🤔" and "?" in text:
            return "🤔"
        if avoid_emoji != "🔥" and "!" in text:
            return "🔥"

        return None

    def _contains_emoji(self, text: str) -> bool:
        """Detect if text already contains at least one emoji character."""
        for char in text:
            code_point = ord(char)
            if (
                0x1F300 <= code_point <= 0x1FAFF
                or 0x2600 <= code_point <= 0x26FF
                or 0x2700 <= code_point <= 0x27BF
            ):
                return True
        return False


if __name__ == "__main__":
    # Test the subtitle generator
    generator = SubtitleGenerator()
