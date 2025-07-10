#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import json

from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor
from modules.subtitle_generator import SubtitleGenerator
from utils.helpers import (
    check_dependencies, 
    select_moments, 
    estimate_processing_time,
    create_summary_report,
    format_time,
    ProgressBar
)
from config import VIDEO_QUALITY, DEFAULT_NUM_CLIPS


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Video Viral Moment Extractor - Automatically extract viral moments with animated subtitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "https://youtube.com/watch?v=..." 
  python main.py --url "https://youtube.com/watch?v=..." --quality 1080p --clips 3
  python main.py --url "https://youtube.com/watch?v=..." --no-subtitles
  python main.py --file "path/to/video.mp4" --clips 5
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--url', type=str, help='YouTube video URL')
    input_group.add_argument('--file', type=str, help='Local video file path')
    
    parser.add_argument('--quality', type=str, default=VIDEO_QUALITY, 
                       choices=['360p', '480p', '720p', '1080p'],
                       help='Video download quality (default: %(default)s)')
    parser.add_argument('--clips', type=int, default=DEFAULT_NUM_CLIPS,
                       help='Maximum number of clips to generate (default: %(default)s)')
    parser.add_argument('--no-subtitles', action='store_true',
                       help='Skip adding subtitles to clips')
    parser.add_argument('--force-transcribe', action='store_true',
                       help='Force re-transcription even if transcript exists')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory for clips')
    parser.add_argument('--format', type=str, default='vertical',
                       choices=['vertical', 'horizontal'],
                       help='Output format: vertical (9:16) for social media or horizontal (16:9) (default: vertical)')
    
    args = parser.parse_args()
    
    print("\n🎬 YouTube Video Viral Moment Extractor")
    print("=" * 50)
    
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and try again.")
        sys.exit(1)
    
    try:
        if args.url:
            print(f"\n📥 Downloading video from YouTube...")
            downloader = YouTubeDownloader()
            video_metadata = downloader.download(args.url, args.quality)
            video_path = video_metadata['filepath']
            print(f"✅ Downloaded: {video_metadata['title']}")
        else:
            video_path = args.file
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            processor = VideoProcessor()
            video_info = processor.get_video_info(video_path)
            video_metadata = {
                'title': Path(video_path).stem,
                'duration': video_info['duration'],
                'filepath': video_path,
                'url': 'Local file'
            }
            print(f"✅ Using local file: {Path(video_path).name}")
        
        print(f"\n🎧 Transcribing audio with Whisper...")
        print(f"Estimated time: {format_time(video_metadata['duration'] * 0.3)}")
        
        transcriber = VideoTranscriber()
        transcript = transcriber.transcribe(video_path, force=args.force_transcribe)
        print(f"✅ Transcription complete: {len(transcript['segments'])} segments")
        
        print(f"\n🤖 Analyzing transcript for viral moments...")
        analyzer = ViralMomentAnalyzer()
        viral_moments = analyzer.analyze_transcript(transcript)
        
        if not viral_moments:
            print("\n❌ No viral moments found with sufficient score.")
            print("Try a different video or adjust the viral score threshold.")
            sys.exit(0)
        
        print(f"✅ Found {len(viral_moments)} potential viral moments!")
        
        selected_moments = select_moments(viral_moments, args.clips)
        
        if not selected_moments:
            print("\n❌ No moments selected.")
            sys.exit(0)
        
        print(f"\n✂️  Extracting {len(selected_moments)} clips...")
        processor = VideoProcessor()
        
        refined_moments = analyzer.refine_moments(selected_moments, transcript)
        validated_moments = processor.validate_timestamps(video_path, refined_moments)
        
        progress = ProgressBar(len(validated_moments), "Extracting clips")
        clip_paths = []
        
        for i, moment in enumerate(validated_moments):
            try:
                output_name = f"viral_clip_{i+1}_score_{moment['score']:.1f}"
                clip_path = processor.extract_clip(
                    video_path,
                    moment['start'],
                    moment['end'],
                    output_name,
                    vertical_format=(args.format == 'vertical')
                )
                clip_paths.append(clip_path)
                
                import json
                metadata_path = Path(clip_path).with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump({
                        'original_video': str(video_path),
                        'start_time': moment['start'],
                        'end_time': moment['end'],
                        'duration': moment['duration'],
                        'score': moment['score'],
                        'reason': moment['reason'],
                        'original_start': moment.get('original_start', moment['start']),
                        'original_end': moment.get('original_end', moment['end'])
                    }, f, indent=2)
                
                progress.update()
            except Exception as e:
                print(f"\n⚠️  Failed to extract clip {i+1}: {e}")
        
        progress.finish()
        print(f"✅ Extracted {len(clip_paths)} clips successfully!")
        
        if not args.no_subtitles and clip_paths:
            print(f"\n🎨 Adding animated subtitles to clips...")
            generator = SubtitleGenerator()
            
            if args.output_dir:
                generator.output_dir = Path(args.output_dir)
                generator.output_dir.mkdir(exist_ok=True)
            
            progress = ProgressBar(len(clip_paths), "Adding subtitles")
            final_clips = []
            
            for clip_path in clip_paths:
                try:
                    metadata_path = Path(clip_path).with_suffix('.json')
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    output_name = Path(clip_path).stem
                    subtitled_path = generator.add_subtitles(
                        clip_path,
                        transcript,
                        metadata.get('original_start', metadata['start_time']),
                        metadata.get('original_end', metadata['end_time']),
                        output_name,
                        vertical_format=(args.format == 'vertical'),
                        clip_start_time=metadata['start_time']
                    )
                    final_clips.append(subtitled_path)
                    progress.update()
                except Exception as e:
                    print(f"\n⚠️  Failed to add subtitles: {e}")
                    final_clips.append(clip_path)
            
            progress.finish()
            print(f"✅ Added subtitles to {len(final_clips)} clips!")
        else:
            final_clips = clip_paths
        
        summary_path = create_summary_report(video_metadata, validated_moments, final_clips)
        
        print("\n🎉 Processing complete!")
        print(f"📁 Output directory: {Path(final_clips[0]).parent if final_clips else 'outputs/'}")
        print(f"📊 Generated {len(final_clips)} viral clips")
        
        if final_clips:
            print("\n📹 Generated clips:")
            for i, clip in enumerate(final_clips):
                print(f"   {i+1}. {Path(clip).name}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()