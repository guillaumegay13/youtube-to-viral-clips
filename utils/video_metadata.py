from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import ffmpeg

from config import VIDEO_INFO_CACHE_SIZE


def _video_cache_key(video_path: str) -> Tuple[str, int, int]:
    path = Path(video_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    resolved_path = path.resolve()
    stat = resolved_path.stat()
    return str(resolved_path), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=VIDEO_INFO_CACHE_SIZE)
def _probe_video_cached(resolved_path: str, mtime_ns: int, size: int) -> Dict[str, Any]:
    # mtime_ns and size are part of the cache key so stale probe data is invalidated
    # if the underlying file changes.
    _ = (mtime_ns, size)

    probe = ffmpeg.probe(resolved_path)
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
        None,
    )
    audio_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
        None,
    )

    info = {
        'duration': float(
            (probe.get('format') or {}).get('duration')
            or (video_stream or {}).get('duration')
            or 0.0
        ),
        'size': int((probe.get('format') or {}).get('size') or 0),
        'bit_rate': int((probe.get('format') or {}).get('bit_rate') or 0),
        'format': (probe.get('format') or {}).get('format_name', ''),
    }

    if video_stream:
        fps_value = video_stream.get('r_frame_rate', '0/1')
        info.update({
            'width': int(video_stream.get('width') or 0),
            'height': int(video_stream.get('height') or 0),
            'video_codec': video_stream.get('codec_name', ''),
            'fps': float(Fraction(fps_value)) if fps_value != '0/0' else 0.0,
        })

    if audio_stream:
        info.update({
            'audio_codec': audio_stream.get('codec_name', ''),
            'audio_sample_rate': int(audio_stream.get('sample_rate') or 0),
            'audio_channels': int(audio_stream.get('channels') or 0),
        })

    return info


def get_video_info(video_path: str) -> Dict[str, Any]:
    resolved_path, mtime_ns, size = _video_cache_key(video_path)
    return dict(_probe_video_cached(resolved_path, mtime_ns, size))
