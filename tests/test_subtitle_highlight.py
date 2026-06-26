import pytest

pytest.importorskip("ffmpeg")

from modules.subtitle_generator import SubtitleGenerator


@pytest.fixture
def generator(tmp_path):
    return SubtitleGenerator(output_dir=tmp_path)


def _words(*entries):
    return [{'word': word, 'start': start, 'end': end} for word, start, end in entries]


def test_group_words_keeps_per_word_timings(generator):
    words = _words(("This", 10.0, 10.3), ("is", 10.3, 10.5), ("huge", 10.5, 11.0))

    groups = generator._group_words(words, max_words=3)

    assert len(groups) == 1
    group = groups[0]
    assert group['text'] == "This is huge"
    assert [w['word'] for w in group['words']] == ["This", "is", "huge"]
    assert group['words'][0]['start'] == 10.0
    assert group['words'][-1]['end'] == 11.0


def test_highlight_events_one_per_word(generator):
    group = {
        'text': "This is huge",
        'start': 10.0,
        'end': 11.0,
        'words': _words(("This", 10.0, 10.3), ("is", 10.3, 10.5), ("huge", 10.5, 11.0)),
    }
    style = {'highlight_color': (255, 220, 0), 'highlight_scale': 115}

    events = generator._build_highlight_events(group, style, video_offset=10.0,
                                               primary_color="&H00FFFFFF")

    assert len(events) == 3

    # Events tile the group with no gaps: each ends where the next starts
    starts = [event[0] for event in events]
    ends = [event[1] for event in events]
    assert starts[0] == pytest.approx(0.0)
    assert ends[-1] == pytest.approx(1.0)
    assert ends[0] == pytest.approx(starts[1])
    assert ends[1] == pytest.approx(starts[2])

    # The active word (and only it) carries the highlight override
    yellow = "&H0000DCFF"  # (255, 220, 0) in ASS BGR order
    first_text = events[0][2]
    assert first_text.count(yellow) == 1
    assert first_text.startswith(f"{{\\c{yellow}\\fscx115\\fscy115}}This")
    assert "is huge" in first_text

    second_text = events[1][2]
    assert f"{{\\c{yellow}\\fscx115\\fscy115}}is" in second_text
    assert second_text.startswith("This ")


def test_highlight_skips_zero_duration_words(generator):
    group = {
        'text': "Hey there",
        'start': 5.0,
        'end': 5.6,
        'words': _words(("Hey", 5.0, 5.0), ("there", 5.0, 5.6)),
    }
    style = {'highlight_color': 'yellow'}

    events = generator._build_highlight_events(group, style, video_offset=5.0,
                                               primary_color="&H00FFFFFF")

    # "Hey" spans zero time (next word starts immediately), so only one event
    assert len(events) == 1
    assert "there" in events[0][2]


def test_emoji_is_appended_but_never_highlighted(generator):
    group = {
        'text': "Make money 💰",
        'start': 0.0,
        'end': 1.0,
        'emoji': "💰",
        'words': _words(("Make", 0.0, 0.5), ("money", 0.5, 1.0)),
    }
    style = {'highlight_color': (255, 220, 0)}

    events = generator._build_highlight_events(group, style, video_offset=0.0,
                                               primary_color="&H00FFFFFF")

    for _, _, text in events:
        # Emoji fallback symbol ($) is present at the end, after the reset tag
        assert text.rstrip().endswith("$")


def test_ass_file_uses_highlight_when_template_has_color(generator):
    word_groups = [{
        'text': "This is huge",
        'start': 0.0,
        'end': 1.0,
        'words': _words(("This", 0.0, 0.3), ("is", 0.3, 0.5), ("huge", 0.5, 1.0)),
    }]
    style = {
        'fontsize': 110, 'color': (255, 255, 255), 'stroke_color': (0, 0, 0),
        'stroke_width': 7, 'position': 0.7, 'highlight_color': (255, 220, 0),
        'highlight_scale': 115,
    }

    ass_path = generator._create_ass_file(word_groups, style, video_offset=0.0)
    try:
        with open(ass_path, encoding='utf-8') as f:
            content = f.read()
    finally:
        import os
        os.unlink(ass_path)

    # One Dialogue line per word instead of one per group
    assert content.count("Dialogue:") == 3
    assert "\\fscx115" in content


def test_ass_file_static_without_highlight_color(generator):
    word_groups = [{
        'text': "This is huge",
        'start': 0.0,
        'end': 1.0,
        'words': _words(("This", 0.0, 0.3), ("is", 0.3, 0.5), ("huge", 0.5, 1.0)),
    }]
    style = {
        'fontsize': 100, 'color': (255, 255, 255), 'stroke_color': (0, 0, 0),
        'stroke_width': 5, 'position': 0.7,
    }

    ass_path = generator._create_ass_file(word_groups, style, video_offset=0.0)
    try:
        with open(ass_path, encoding='utf-8') as f:
            content = f.read()
    finally:
        import os
        os.unlink(ass_path)

    assert content.count("Dialogue:") == 1
    assert "\\fscx" not in content


def test_seam_caption_is_pinned_to_exact_center(generator):
    # position 0.5 -> split-stack seam: libass middle-alignment renders below
    # the geometric center, so we pin the caption with \pos at exact center.
    word_groups = [{
        'text': "This is huge",
        'start': 0.0,
        'end': 1.0,
        'words': _words(("This", 0.0, 0.3), ("is", 0.3, 0.5), ("huge", 0.5, 1.0)),
    }]
    style = {
        'fontsize': 100, 'color': (255, 255, 255), 'stroke_color': (0, 0, 0),
        'stroke_width': 5, 'position': 0.5,
    }

    ass_path = generator._create_ass_file(word_groups, style, video_offset=0.0,
                                          video_width=1080, video_height=1920)
    try:
        with open(ass_path, encoding='utf-8') as f:
            content = f.read()
    finally:
        import os
        os.unlink(ass_path)

    # Centered horizontally (1080/2) on the exact vertical center (0.5 * 1920)
    assert "\\pos(540,960)" in content


def test_bottom_caption_has_no_pos_override(generator):
    word_groups = [{
        'text': "This is huge",
        'start': 0.0,
        'end': 1.0,
        'words': _words(("This", 0.0, 0.3), ("is", 0.3, 0.5), ("huge", 0.5, 1.0)),
    }]
    style = {
        'fontsize': 100, 'color': (255, 255, 255), 'stroke_color': (0, 0, 0),
        'stroke_width': 5, 'position': 0.85,
    }

    ass_path = generator._create_ass_file(word_groups, style, video_offset=0.0,
                                          video_width=1080, video_height=1920)
    try:
        with open(ass_path, encoding='utf-8') as f:
            content = f.read()
    finally:
        import os
        os.unlink(ass_path)

    # Bottom-positioned styles keep margin-based placement, no \pos pin
    assert "\\pos(" not in content
