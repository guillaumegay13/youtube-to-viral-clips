import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import shutil
import platform
import os

from config import SUBTITLE_STYLE, VERTICAL_SUBTITLE_STYLE, OUTPUTS_DIR
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
                     clip_start_time: Optional[float] = None) -> str:
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
            
            # Get subtitle style
            style = VERTICAL_SUBTITLE_STYLE if vertical_format else SUBTITLE_STYLE
            
            # Setup font
            try:
                font = ImageFont.truetype(self.font_path, style['fontsize'])
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
            
            print(f"Adding subtitles to {total_frames} frames ({len(words)} words)...")
            
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                current_time = frame_count / fps
                video_time = video_offset + current_time
                
                # Find current word(s) to display
                current_words = []
                for word_data in words:
                    if word_data['start'] <= video_time <= word_data['end']:
                        current_words.append(word_data['word'])
                
                if current_words:
                    # Join words that appear at the same time
                    current_text = ' '.join(current_words)
                    
                    # Convert frame to PIL Image
                    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(img_pil)
                    
                    # Calculate text position
                    bbox = draw.textbbox((0, 0), current_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # Position based on style
                    x = (width - text_width) // 2
                    y_position = style['position'][1] if isinstance(style['position'][1], (int, float)) else 0.7
                    y = int(height * y_position) - text_height // 2
                    
                    # Draw text with outline (stroke)
                    stroke_width = style['stroke_width']
                    stroke_color = (0, 0, 0)  # Black outline
                    text_color = (255, 255, 255)  # White text
                    
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


if __name__ == "__main__":
    # Test the subtitle generator
    generator = SubtitleGenerator()
    print(f"Using font: {generator.font_path}")