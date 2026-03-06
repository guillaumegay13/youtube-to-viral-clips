import pytest

pytest.importorskip("ollama")

from modules.analyzer import ViralMomentAnalyzer


def _build_segments(count=18, duration=4.0):
    segments = []
    current = 0.0
    for index in range(count):
        segments.append({
            "start": current,
            "end": current + duration,
            "text": f"segment {index}",
        })
        current += duration
    return segments


def _naive_sliding_chunks(segments, window, overlap):
    step = window - overlap
    total_duration = segments[-1]["end"]
    chunks = []
    window_start = 0.0

    while window_start < total_duration:
        window_end = window_start + window
        chunk_segments = [
            segment
            for segment in segments
            if segment["end"] > window_start and segment["start"] < window_end
        ]
        if chunk_segments:
            chunks.append({
                "start": chunk_segments[0]["start"],
                "end": chunk_segments[-1]["end"],
                "text": " ".join(segment["text"] for segment in chunk_segments),
                "segments": chunk_segments,
            })
        window_start += step

    return chunks


def test_sliding_chunk_builder_matches_previous_behavior():
    analyzer = object.__new__(ViralMomentAnalyzer)
    segments = _build_segments(count=20, duration=3.0)

    actual = analyzer._create_sliding_chunks(segments)
    expected = _naive_sliding_chunks(segments, window=45, overlap=15)

    assert actual == expected


def test_prefilter_ranks_hook_heavy_chunk_first():
    analyzer = object.__new__(ViralMomentAnalyzer)
    bland_chunk = {
        "start": 0.0,
        "end": 30.0,
        "text": "this is a calm explanation about a regular workflow",
        "segments": [
            {"start": 0.0, "end": 10.0, "text": "this is a calm explanation"},
            {"start": 10.0, "end": 20.0, "text": "about a regular workflow"},
            {"start": 20.0, "end": 30.0, "text": "with no strong hook"},
        ],
    }
    hook_chunk = {
        "start": 30.0,
        "end": 60.0,
        "text": "you won't believe the shocking secret that changed everything!",
        "segments": [
            {"start": 30.0, "end": 40.0, "text": "you won't believe"},
            {"start": 40.6, "end": 50.0, "text": "the shocking secret"},
            {"start": 50.0, "end": 60.0, "text": "that changed everything!"},
        ],
    }

    hook_score = analyzer._score_chunk_for_prefilter(hook_chunk, "en")
    bland_score = analyzer._score_chunk_for_prefilter(bland_chunk, "en")
    ranked, _ = analyzer._rank_chunks_for_analysis(
        [bland_chunk] * 29 + [hook_chunk],
        "en",
    )

    assert hook_score > bland_score
    assert ranked[0] is hook_chunk
