from types import SimpleNamespace

from modules.transcriber import VideoTranscriber


def test_faster_whisper_serializer_preserves_transcript_shape():
    transcriber = VideoTranscriber()
    raw_segments = [
        SimpleNamespace(
            id=7,
            start=1.25,
            end=4.75,
            text=" Hello world ",
            words=[
                SimpleNamespace(word=" Hello", start=1.25, end=1.8, probability=0.92),
                SimpleNamespace(word=" world ", start=1.8, end=2.4, probability=0.0),
            ],
        ),
    ]

    serialized = transcriber._serialize_faster_whisper_segments(raw_segments)

    assert serialized == [{
        "id": 7,
        "start": 1.25,
        "end": 4.75,
        "text": "Hello world",
        "words": [
            {"word": "Hello", "start": 1.25, "end": 1.8, "probability": 0.92},
            {"word": "world", "start": 1.8, "end": 2.4, "probability": 0.0},
        ],
    }]


def test_cache_signature_tracks_backend_settings():
    transcriber = VideoTranscriber()

    signature = transcriber._cache_signature(language="fr")

    assert signature["backend"] == "faster-whisper"
    assert signature["language"] == "fr"
    assert signature["word_timestamps"] is True
