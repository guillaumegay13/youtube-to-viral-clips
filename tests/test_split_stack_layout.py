import pytest

pytest.importorskip("ffmpeg")

from modules.video_processor import (
    VERTICAL_HEIGHT,
    VERTICAL_WIDTH,
    compute_split_stack_regions,
)

PANEL_ASPECT = VERTICAL_WIDTH / (VERTICAL_HEIGHT // 2)  # 9:8


def test_regions_for_1080p_source():
    left, right = compute_split_stack_regions(1920, 1080)

    # Each panel is a full half-width crop at 9:8 aspect
    assert left['width'] == 960
    assert left['height'] == 852
    assert right['width'] == left['width']
    assert right['height'] == left['height']

    # Right panel starts at the horizontal midpoint
    assert left['x'] == 0
    assert right['x'] == 960

    # Face bias keeps the crop above center
    assert 0 < left['y'] < (1080 - left['height']) // 2 + 1
    assert right['y'] == left['y']


def test_regions_stay_within_frame():
    for width, height in [(1920, 1080), (3840, 2160), (1280, 720), (854, 480)]:
        for region in compute_split_stack_regions(width, height):
            assert region['x'] >= 0
            assert region['y'] >= 0
            assert region['x'] + region['width'] <= width
            assert region['y'] + region['height'] <= height


def test_regions_have_even_dimensions():
    # Odd source dimensions must not produce odd crop sizes (ffmpeg requirement)
    for width, height in [(1919, 1079), (1280, 719), (1366, 768)]:
        for region in compute_split_stack_regions(width, height):
            assert region['width'] % 2 == 0
            assert region['height'] % 2 == 0


def test_panel_aspect_matches_stacked_canvas():
    for width, height in [(1920, 1080), (3840, 2160), (2560, 1440)]:
        left, _ = compute_split_stack_regions(width, height)
        aspect = left['width'] / left['height']
        assert aspect == pytest.approx(PANEL_ASPECT, rel=0.01)


def test_short_source_clamps_to_frame_height():
    # Ultra-wide source: half-width crop at 9:8 would exceed the frame height,
    # so the crop must clamp to the full height and narrow the width instead.
    left, right = compute_split_stack_regions(3440, 1080)
    assert left['height'] <= 1080
    assert left['width'] / left['height'] == pytest.approx(PANEL_ASPECT, rel=0.01)
    # Panels stay centered inside their halves
    assert left['x'] > 0
    assert right['x'] >= 3440 // 2
