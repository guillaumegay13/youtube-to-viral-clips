from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

from config import SUBTITLE_STYLE, VERTICAL_SUBTITLE_STYLE, OUTPUTS_DIR
from modules.transcriber import VideoTranscriber


class SubtitleGenerator:
    def __init__(self, output_dir: Path = OUTPUTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.transcriber = VideoTranscriber()
        
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
            print(f"Loading video clip...")
            video = VideoFileClip(str(video_path))
            
            # If clip_start_time is provided, it means the clip was extracted with a buffer
            if clip_start_time is not None:
                # Adjust the range to get words from the entire clip duration
                words = self.transcriber.get_words_in_range(transcript, clip_start_time, clip_start_time + video.duration)
                video_offset = clip_start_time
            else:
                words = self.transcriber.get_words_in_range(transcript, start_time, end_time)
                video_offset = start_time
            
            print(f"Found {len(words)} words for subtitles in range {start_time:.1f}s - {end_time:.1f}s (clip_start: {clip_start_time})")
            
            if not words:
                print("No words found in the specified time range")
                video.write_videofile(str(output_path), codec='libx264', audio_codec='aac')
                return str(output_path)
            
            subtitle_clips = self._create_subtitle_clips(words, video_offset, video.duration, vertical_format)
            
            print(f"Created {len(subtitle_clips)} subtitle clips")
            
            if not subtitle_clips:
                print("WARNING: No subtitle clips were created!")
                video.write_videofile(str(output_path), codec='libx264', audio_codec='aac')
                return str(output_path)
            
            final_video = CompositeVideoClip([video] + subtitle_clips)
            
            print(f"Rendering video with subtitles...")
            final_video.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=video.fps
            )
            
            video.close()
            final_video.close()
            
            print(f"Video with subtitles saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            raise Exception(f"Error adding subtitles: {str(e)}")
    
    def _create_subtitle_clips(self, words: List[Dict], video_start: float, 
                              video_duration: float, vertical_format: bool = True) -> List[TextClip]:
        subtitle_clips = []
        
        print(f"Creating {len(words)} subtitle clips...")
        
        for i, word_data in enumerate(words):
            word_start = word_data['start'] - video_start
            word_end = word_data['end'] - video_start
            
            if i < 5:  # Debug first 5 words
                print(f"Word '{word_data['word']}': original={word_data['start']:.2f}-{word_data['end']:.2f}, adjusted={word_start:.2f}-{word_end:.2f}, video_start={video_start:.2f}")
            
            if word_start < 0:
                word_start = 0
            if word_end > video_duration:
                word_end = video_duration
            
            if word_start >= video_duration or word_end <= 0:
                continue
            
            duration = word_end - word_start
            if duration <= 0:
                continue
            
            try:
                style = VERTICAL_SUBTITLE_STYLE if vertical_format else SUBTITLE_STYLE
                
                txt_clip = TextClip(
                    word_data['word'],
                    fontsize=style['fontsize'],
                    font=style['font'],
                    color=style['color'],
                    stroke_color=style['stroke_color'],
                    stroke_width=style['stroke_width'],
                    method=style['method'],
                    size=(None, None)  
                )
                
                txt_clip = txt_clip.set_position(style['position'])
                txt_clip = txt_clip.set_start(word_start)
                txt_clip = txt_clip.set_duration(duration)
                
                fade_duration = min(0.1, duration * 0.2)
                txt_clip = txt_clip.crossfadein(fade_duration)
                
                subtitle_clips.append(txt_clip)
                
            except Exception as e:
                print(f"Warning: Failed to create subtitle for word '{word_data['word']}': {e}")
                continue
        
        return subtitle_clips
    
    def add_subtitles_to_clips(self, clip_paths: List[str], transcript: Dict) -> List[str]:
        output_paths = []
        
        for clip_path in clip_paths:
            try:
                metadata_path = Path(clip_path).with_suffix('.json')
                if metadata_path.exists():
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    start_time = metadata['start_time']
                    end_time = metadata['end_time']
                    
                    output_name = Path(clip_path).stem
                    output_path = self.add_subtitles(
                        clip_path, 
                        transcript, 
                        start_time, 
                        end_time,
                        output_name
                    )
                    output_paths.append(output_path)
                else:
                    print(f"Warning: No metadata found for {clip_path}")
                    
            except Exception as e:
                print(f"Failed to add subtitles to {clip_path}: {e}")
                continue
        
        return output_paths
    
    def create_word_by_word_style(self, words: List[Dict], style_preset: str = "default") -> List[Dict]:
        style_presets = {
            "default": SUBTITLE_STYLE,
            "minimal": {
                "font": "Arial",
                "fontsize": 40,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "position": ("center", 0.9),
                "method": "caption"
            },
            "bold": {
                "font": "Arial-Black",
                "fontsize": 70,
                "color": "yellow",
                "stroke_color": "black",
                "stroke_width": 4,
                "position": ("center", 0.8),
                "method": "caption"
            }
        }
        
        style = style_presets.get(style_preset, style_presets["default"])
        
        styled_words = []
        for word in words:
            styled_word = word.copy()
            styled_word.update({"style": style})
            styled_words.append(styled_word)
        
        return styled_words


if __name__ == "__main__":
    generator = SubtitleGenerator()
    
    video_path = input("Enter video file path: ")
    transcript_path = input("Enter transcript JSON file path: ")
    
    try:
        import json
        with open(transcript_path, 'r') as f:
            transcript = json.load(f)
        
        video_info = VideoProcessor().get_video_info(video_path)
        output_path = generator.add_subtitles(
            video_path, 
            transcript, 
            0, 
            video_info['duration']
        )
        print(f"Video with subtitles created: {output_path}")
    except Exception as e:
        print(f"Error: {e}")