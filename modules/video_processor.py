import ffmpeg
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import os

from config import OUTPUTS_DIR, VIDEO_CODEC, AUDIO_CODEC, CLIP_BUFFER_SECONDS


class VideoProcessor:
    def __init__(self, output_dir: Path = OUTPUTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_clip(self, video_path: str, start_time: float, end_time: float, 
                    output_name: Optional[str] = None, vertical_format: bool = True) -> str:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        duration = end_time - start_time
        
        if output_name:
            output_filename = f"{output_name}.mp4"
        else:
            output_filename = f"{video_path.stem}_clip_{int(start_time)}_{int(end_time)}.mp4"
        
        output_path = self.output_dir / output_filename
        
        try:
            print(f"Extracting clip: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")
            
            input_stream = ffmpeg.input(str(video_path), ss=start_time, t=duration)
            
            if vertical_format:
                # Get video info to calculate crop
                probe = ffmpeg.probe(str(video_path))
                video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                
                # Calculate 9:16 crop (vertical format for social media)
                target_aspect = 9 / 16
                current_aspect = width / height
                
                if current_aspect > target_aspect:
                    # Video is wider than 9:16, crop width
                    new_width = int(height * target_aspect)
                    new_height = height
                    x_offset = (width - new_width) // 2
                    y_offset = 0
                else:
                    # Video is taller than 9:16, crop height
                    new_width = width
                    new_height = int(width / target_aspect)
                    x_offset = 0
                    y_offset = (height - new_height) // 2
                
                # Split input into video and audio streams
                video = input_stream.video
                audio = input_stream.audio
                
                # Apply crop and scale filters to video only
                video = ffmpeg.filter(video, 'crop', new_width, new_height, x_offset, y_offset)
                video = ffmpeg.filter(video, 'scale', 1080, 1920)
                
                # Combine video and audio streams
                stream = ffmpeg.output(
                    video, audio,
                    str(output_path),
                    vcodec=VIDEO_CODEC,
                    acodec=AUDIO_CODEC,
                    preset='medium',
                    crf=23,
                    **{'b:a': '128k'}
                )
            else:
                stream = ffmpeg.output(
                    input_stream,
                    str(output_path),
                    vcodec=VIDEO_CODEC,
                    acodec=AUDIO_CODEC,
                    preset='medium',
                    crf=23,
                    **{'b:a': '128k'}
                )
            
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            if not output_path.exists():
                raise Exception("Output file was not created")
            
            print(f"Clip saved to: {output_path}")
            return str(output_path)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise Exception(f"FFmpeg error: {error_msg}")
        except Exception as e:
            raise Exception(f"Error extracting clip: {str(e)}")
    
    def extract_multiple_clips(self, video_path: str, moments: List[Dict], 
                             prefix: str = "viral_clip") -> List[str]:
        output_paths = []
        
        for i, moment in enumerate(moments):
            try:
                output_name = f"{prefix}_{i+1}_score_{moment['score']:.1f}"
                output_path = self.extract_clip(
                    video_path,
                    moment['start'],
                    moment['end'],
                    output_name
                )
                output_paths.append(output_path)
                
                metadata_path = Path(output_path).with_suffix('.json')
                import json
                with open(metadata_path, 'w') as f:
                    json.dump({
                        'original_video': str(video_path),
                        'start_time': moment['start'],
                        'end_time': moment['end'],
                        'duration': moment['duration'],
                        'score': moment['score'],
                        'reason': moment['reason'],
                        'text_preview': moment.get('text', '')
                    }, f, indent=2)
                    
            except Exception as e:
                print(f"Failed to extract clip {i+1}: {e}")
                continue
        
        return output_paths
    
    def get_video_info(self, video_path: str) -> Dict:
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), 
                None
            )
            audio_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), 
                None
            )
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'bit_rate': int(probe['format']['bit_rate']),
                'format': probe['format']['format_name']
            }
            
            if video_stream:
                info.update({
                    'width': int(video_stream['width']),
                    'height': int(video_stream['height']),
                    'video_codec': video_stream['codec_name'],
                    'fps': eval(video_stream['r_frame_rate'])
                })
            
            if audio_stream:
                info.update({
                    'audio_codec': audio_stream['codec_name'],
                    'audio_sample_rate': int(audio_stream['sample_rate']),
                    'audio_channels': int(audio_stream['channels'])
                })
            
            return info
            
        except Exception as e:
            raise Exception(f"Error getting video info: {str(e)}")
    
    def validate_timestamps(self, video_path: str, moments: List[Dict]) -> List[Dict]:
        video_info = self.get_video_info(video_path)
        video_duration = video_info['duration']
        
        valid_moments = []
        for moment in moments:
            if moment['start'] < 0:
                moment['start'] = 0
            if moment['end'] > video_duration:
                moment['end'] = video_duration
            
            if moment['start'] < moment['end']:
                moment['duration'] = moment['end'] - moment['start']
                valid_moments.append(moment)
            else:
                print(f"Skipping invalid moment: start={moment['start']}, end={moment['end']}")
        
        return valid_moments


if __name__ == "__main__":
    processor = VideoProcessor()
    
    video_path = input("Enter video file path: ")
    start_time = float(input("Enter start time (seconds): "))
    end_time = float(input("Enter end time (seconds): "))
    
    try:
        output_path = processor.extract_clip(video_path, start_time, end_time)
        print(f"Clip successfully created: {output_path}")
    except Exception as e:
        print(f"Error: {e}")