import pytest

pytest.importorskip("ffmpeg")

from utils import video_metadata


def test_get_video_info_reuses_cached_probe(monkeypatch, tmp_path):
    video_metadata._probe_video_cached.cache_clear()

    probe_calls = {"count": 0}

    def fake_probe(path):
        probe_calls["count"] += 1
        return {
            "format": {
                "duration": "12.5",
                "size": "1024",
                "bit_rate": "64000",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "codec_name": "h264",
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        }

    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake-video")
    monkeypatch.setattr(video_metadata.ffmpeg, "probe", fake_probe)

    first = video_metadata.get_video_info(str(video_path))
    second = video_metadata.get_video_info(str(video_path))

    assert probe_calls["count"] == 1
    assert first == second
    assert first["width"] == 1920
    assert first["audio_codec"] == "aac"
