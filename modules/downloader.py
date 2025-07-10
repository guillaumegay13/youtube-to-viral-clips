import os
import json
from pathlib import Path
import yt_dlp
from typing import Dict, Optional
import re

from config import DOWNLOADS_DIR, VIDEO_QUALITY, MAX_VIDEO_SIZE_MB


class YouTubeDownloader:
    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    def _sanitize_filename(self, filename: str) -> str:
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename[:200]  
    
    def download(self, url: str, quality: str = VIDEO_QUALITY) -> Dict[str, any]:
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        ydl_opts = {
            'format': f'best[height<={quality[:-1]}][ext=mp4]/best[height<={quality[:-1]}]/best',
            'outtmpl': str(self.output_dir / '%(title)s_%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_playlist': True,
            'max_filesize': MAX_VIDEO_SIZE_MB * 1024 * 1024,  
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Fetching video information for: {url}")
                info_dict = ydl.extract_info(url, download=False)
                
                title = info_dict.get('title', 'Unknown')
                duration = info_dict.get('duration', 0)
                
                if duration > 3600:  
                    raise ValueError(f"Video too long: {duration} seconds. Maximum allowed: 3600 seconds")
                
                print(f"Downloading: {title}")
                info_dict = ydl.extract_info(url, download=True)
                
                filename = ydl.prepare_filename(info_dict)
                if not filename.endswith('.mp4'):
                    filename = filename.rsplit('.', 1)[0] + '.mp4'
                
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
                
                print(f"Download complete: {filepath}")
                print(f"Video duration: {duration} seconds")
                
                return metadata
                
        except yt_dlp.utils.DownloadError as e:
            raise Exception(f"Download failed: {str(e)}")
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
        print(f"Successfully downloaded: {metadata['title']}")
    except Exception as e:
        print(f"Error: {e}")