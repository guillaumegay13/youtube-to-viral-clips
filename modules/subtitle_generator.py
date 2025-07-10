import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import shutil
import platform
import os

from config import SUBTITLE_STYLE, VERTICAL_SUBTITLE_STYLE, OUTPUTS_DIR, SUBTITLE_TEMPLATES
from modules.transcriber import VideoTranscriber


class SubtitleGenerator:
    def __init__(self, output_dir: Path = OUTPUTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.transcriber = VideoTranscriber()
        self.font_path = self._get_font_path()
        
    def _get_font_path(self) -> str:
        """Get the appropriate font path for the current system"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial Bold.ttf",
                "/System/Library/Fonts/Avenir Next Bold.ttc"
            ]
        elif system == "Windows":
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/Arial.ttf"
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
        
        # Try to find an existing font
        for path in font_paths:
            if os.path.exists(path):
                return path
        
        # Fallback to default
        print("Warning: Could not find a suitable font file. Subtitles may not appear correctly.")
        return font_paths[0]
    
    def add_subtitles(self, video_path: str, transcript: Dict, 
                     start_time: float, end_time: float,
                     output_name: Optional[str] = None, vertical_format: bool = True,
                     clip_start_time: Optional[float] = None, style_template: str = "Classic",
                     language: str = "en") -> str:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_name:
            output_filename = f"{output_name}_subtitled.mp4"
        else:
            output_filename = f"{video_path.stem}_subtitled.mp4"
        
        output_path = self.output_dir / output_filename
        
        try:
            print(f"Loading video for subtitle processing...")
            cap = cv2.VideoCapture(str(video_path))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Create temporary file for video without audio
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video_path = temp_video.name
            temp_video.close()
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
            
            # Get subtitle style from template
            if style_template in SUBTITLE_TEMPLATES:
                template = SUBTITLE_TEMPLATES[style_template]
                style_settings = template['vertical'] if vertical_format else template['horizontal']
            else:
                # Fallback to default styles
                style = VERTICAL_SUBTITLE_STYLE if vertical_format else SUBTITLE_STYLE
                style_settings = {
                    'fontsize': style['fontsize'],
                    'color': (255, 255, 255) if style['color'] == 'white' else (0, 0, 0),
                    'stroke_color': (0, 0, 0) if style['stroke_color'] == 'black' else (255, 255, 255),
                    'stroke_width': style['stroke_width'],
                    'position': style['position'][1] if isinstance(style['position'], tuple) else style['position']
                }
            
            # Setup font
            try:
                font = ImageFont.truetype(self.font_path, style_settings['fontsize'])
            except:
                print(f"Warning: Could not load font from {self.font_path}, using default")
                font = ImageFont.load_default()
            
            # If clip_start_time is provided, use it as the offset
            if clip_start_time is not None:
                video_offset = clip_start_time
            else:
                video_offset = start_time
            
            # Get words for the entire clip duration
            words = self.transcriber.get_words_in_range(
                transcript, 
                video_offset, 
                video_offset + (total_frames / fps)
            )
            
            # Group words intelligently
            max_words = style_settings.get('max_words', 3)
            word_groups = self._group_words(words, max_words, language)
            
            print(f"Adding subtitles to {total_frames} frames ({len(words)} words in {len(word_groups)} groups)...")
            
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                current_time = frame_count / fps
                video_time = video_offset + current_time
                
                # Find current word group to display
                current_text = None
                for group in word_groups:
                    if group['start'] <= video_time <= group['end']:
                        current_text = group['text']
                        break
                
                if current_text:
                    
                    # Convert frame to PIL Image
                    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(img_pil)
                    
                    # Calculate text position
                    bbox = draw.textbbox((0, 0), current_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # Position based on style
                    x = (width - text_width) // 2
                    y_position = style_settings['position']
                    y = int(height * y_position) - text_height // 2
                    
                    # Draw text with outline (stroke)
                    stroke_width = style_settings['stroke_width']
                    stroke_color = style_settings['stroke_color']
                    text_color = style_settings['color']
                    
                    # Draw stroke
                    for adj_x in range(-stroke_width, stroke_width + 1):
                        for adj_y in range(-stroke_width, stroke_width + 1):
                            if adj_x != 0 or adj_y != 0:
                                draw.text((x + adj_x, y + adj_y), current_text, 
                                         font=font, fill=stroke_color)
                    
                    # Draw main text
                    draw.text((x, y), current_text, font=font, fill=text_color)
                    
                    # Convert back to OpenCV
                    frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                
                out.write(frame)
                frame_count += 1
                
                # Progress indicator
                if frame_count % (fps * 5) == 0:  # Every 5 seconds
                    progress = (frame_count / total_frames) * 100
                    print(f"  Progress: {progress:.1f}%")
            
            cap.release()
            out.release()
            
            print("Merging video with original audio...")
            
            # Use ffmpeg to merge the video with original audio
            import ffmpeg
            
            # Extract audio from original
            audio = ffmpeg.input(str(video_path)).audio
            video = ffmpeg.input(temp_video_path).video
            
            # Combine and output
            stream = ffmpeg.output(
                video, audio,
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                **{'b:a': '128k'}
            )
            
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # Clean up temporary file
            os.unlink(temp_video_path)
            
            print(f"Video with subtitles saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            # Clean up on error
            if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            raise Exception(f"Error adding subtitles: {str(e)}")
    
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
        
        groups = []
        current_group = []
        current_start = None
        current_end = None
        
        for i, word in enumerate(words):
            word_text = word['word'].strip().lower()
            
            # Start a new group if needed
            if current_start is None:
                current_start = word['start']
            
            current_group.append(word['word'].strip())
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


if __name__ == "__main__":
    # Test the subtitle generator
    generator = SubtitleGenerator()
    print(f"Using font: {generator.font_path}")