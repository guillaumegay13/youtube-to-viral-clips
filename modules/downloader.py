import os
import json
from pathlib import Path
import yt_dlp
from typing import Dict, Optional
import re

from config import DOWNLOADS_DIR, VIDEO_QUALITY, MAX_VIDEO_SIZE_MB
from utils.helpers import cleanup_downloads


class YouTubeDownloader:
    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        # Auto-clean downloads older than 24 hours
        cleaned = cleanup_downloads(self.output_dir)
        if cleaned:
            print(f"Cleaned up {cleaned} old download(s)")
        
    def _sanitize_filename(self, filename: str) -> str:
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename[:200]  
    
    def download(self, url: str, quality: str = VIDEO_QUALITY, progress_callback=None) -> Dict[str, any]:
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Parse desired height (e.g., "720p" -> 720). Allow "auto" to skip constraint.
        try:
            target_height = int(quality.lower().replace('p', '')) if quality and quality.lower() != 'auto' else None
        except Exception:
            target_height = None

        # Robust format chain: try separate streams first, fall back to muxed.
        # merge_output_format ensures ffmpeg merges into mp4 when needed.
        if target_height:
            format_expr = (
                f"bestvideo[height<=?{target_height}]+bestaudio/best[height<=?{target_height}]/"
                f"bestvideo+bestaudio/best"
            )
        else:
            format_expr = "bestvideo+bestaudio/best"

        ydl_opts = {
            'format': format_expr,
            'merge_output_format': 'mp4',
            'outtmpl': str(self.output_dir / '%(title)s_%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_playlist': True,
            # Use alternative clients to avoid YouTube 403 errors
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios,mweb'],
                },
            },
        }

        if progress_callback:
            def _hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = (downloaded / total * 100) if total else 0
                    progress_callback(pct, downloaded, total)
            ydl_opts['progress_hooks'] = [_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_meta = ydl.extract_info(url, download=False)
                title = info_meta.get('title', 'Unknown')
                duration = info_meta.get('duration', 0)

                info_dict = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info_dict)
                filepath = Path(filename)

                if not filepath.exists():
                    possible_files = list(self.output_dir.glob(f"*{video_id}*"))
                    if possible_files:
                        filepath = possible_files[0]
                    else:
                        raise FileNotFoundError(f"Downloaded file not found: {filename}")

                metadata = {
                    'video_id': video_id,
                    'title': title,
                    'duration': duration,
                    'description': info_dict.get('description', ''),
                    'upload_date': info_dict.get('upload_date', ''),
                    'uploader': info_dict.get('uploader', ''),
                    'view_count': info_dict.get('view_count', 0),
                    'like_count': info_dict.get('like_count', 0),
                    'filepath': str(filepath),
                    'url': url
                }

                metadata_path = filepath.with_suffix('.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                return metadata

        except yt_dlp.utils.DownloadError as e:
            # Fallback: drop height constraint and try web client
            try:
                fallback_opts = {
                    **ydl_opts,
                    'format': 'bestvideo*+bestaudio/best',
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['mweb,default'],
                        },
                    },
                }
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info_meta = ydl.extract_info(url, download=False)
                    title = info_meta.get('title', 'Unknown')
                    duration = info_meta.get('duration', 0)
                    info_dict = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info_dict)
                    filepath = Path(filename)
                    if not filepath.exists():
                        possible_files = list(self.output_dir.glob(f"*{video_id}*"))
                        if possible_files:
                            filepath = possible_files[0]
                        else:
                            raise FileNotFoundError(f"Downloaded file not found: {filename}")
                    metadata = {
                        'video_id': video_id,
                        'title': title,
                        'duration': duration,
                        'description': info_dict.get('description', ''),
                        'upload_date': info_dict.get('upload_date', ''),
                        'uploader': info_dict.get('uploader', ''),
                        'view_count': info_dict.get('view_count', 0),
                        'like_count': info_dict.get('like_count', 0),
                        'filepath': str(filepath),
                        'url': url
                    }
                    metadata_path = filepath.with_suffix('.json')
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    return metadata
            except Exception as e2:
                raise Exception(f"Download failed: {str(e2)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")

    
    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
            r'youtu\.be\/([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


if __name__ == "__main__":
    downloader = YouTubeDownloader()
    test_url = input("Enter YouTube URL to test: ")
    try:
        metadata = downloader.download(test_url)
        # Download complete
    except Exception as e:
        # Error occurred
        pass
