import streamlit as st
import subprocess
import json
from pathlib import Path
import shutil
import time
from typing import List, Dict

from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor
from modules.subtitle_generator import SubtitleGenerator
from utils.helpers import check_dependencies, format_time
from utils.translations import get_text
from config import DEFAULT_NUM_CLIPS, OUTPUTS_DIR, SUBTITLE_TEMPLATES

# Initialize session state for language
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Page config
st.set_page_config(
    page_title=get_text("page_title", st.session_state.language),
    page_icon="🎬",
    layout="centered"
)

# Custom CSS for black & white theme
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: white;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: black !important;
    }
    
    /* Text */
    p, span, label {
        color: black !important;
    }
    
    /* Captions */
    .caption {
        color: black !important;
    }
    
    [data-testid="caption"] {
        color: black !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: white !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #f0f0f0 !important;
        color: black !important;
        border: 2px solid black !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        background-color: white !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stDownloadButton > button:hover {
        background-color: #f0f0f0 !important;
        color: black !important;
        border: 2px solid black !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        border: 1px solid black;
        border-radius: 4px;
        background-color: white !important;
        color: black !important;
    }
    
    /* Select boxes */
    .stSelectbox > div > div > select {
        border: 1px solid black;
        border-radius: 4px;
        background-color: white !important;
        color: black !important;
    }
    
    /* Selectbox label */
    .stSelectbox > label {
        color: black !important;
    }
    
    /* Selectbox dropdown options */
    .stSelectbox [data-baseweb="select"] {
        background-color: white !important;
        color: black !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
    }
    
    /* Dropdown menu items */
    [data-baseweb="menu"] {
        background-color: white !important;
    }
    
    [data-baseweb="menu"] li {
        background-color: white !important;
        color: black !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background-color: #f0f0f0 !important;
        color: black !important;
    }
    
    /* Checkbox */
    .stCheckbox > label > span {
        color: black !important;
    }
    
    .stCheckbox > label > div[data-baseweb="checkbox"] {
        background-color: white !important;
        border: 2px solid black !important;
    }
    
    .stCheckbox > label > div[data-baseweb="checkbox"]:hover {
        background-color: #f0f0f0 !important;
    }
    
    /* Number input - all possible selectors */
    .stNumberInput > div > div > input {
        border: 1px solid black !important;
        border-radius: 4px;
        background-color: white !important;
        color: black !important;
    }
    
    /* Streamlit's BaseWeb input override */
    [data-baseweb="base-input"] {
        background-color: white !important;
    }
    
    div[data-baseweb="input"] {
        background-color: white !important;
    }
    
    div[data-baseweb="input"] > div {
        background-color: white !important;
    }
    
    /* Target the actual input element inside BaseWeb */
    input[inputmode="numeric"] {
        background-color: white !important;
        color: black !important;
    }
    
    /* Number input container */
    .stNumberInput input {
        background-color: white !important;
        color: black !important;
        -webkit-appearance: none;
    }
    
    /* Force all inputs to be white */
    input {
        background-color: white !important;
        color: black !important;
    }
    
    /* Number input buttons (increment/decrement) */
    .stNumberInput button {
        background-color: white !important;
        border: 1px solid black !important;
        color: black !important;
    }
    
    .stNumberInput button:hover {
        background-color: #f0f0f0 !important;
    }
    
    /* Ensure all form containers have white background */
    .stForm {
        background-color: white !important;
    }
    
    /* Dropdown menus */
    .stSelectbox > div > div > div {
        background-color: white !important;
    }
    
    /* Text area if needed */
    .stTextArea > div > div > textarea {
        border: 1px solid black;
        border-radius: 4px;
        background-color: white !important;
        color: black !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: black;
    }
    
    /* Success/Error/Info messages */
    .stAlert {
        background-color: #f0f0f0;
        color: black;
        border: 1px solid black;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f0f0f0;
        color: black;
        border: 1px solid black;
    }
</style>
""", unsafe_allow_html=True)

# Language switcher in the top right
col1, col2, col3 = st.columns([4, 1, 1])
with col3:
    if st.button("🇫🇷 FR" if st.session_state.language == 'en' else "🇬🇧 EN", 
                 key="lang_switch",
                 help="Switch language / Changer de langue"):
        st.session_state.language = 'fr' if st.session_state.language == 'en' else 'en'
        st.rerun()

# Title
st.title(get_text("app_title", st.session_state.language))
st.markdown(get_text("app_subtitle", st.session_state.language))

# Check dependencies
if not check_dependencies():
    st.error(get_text("missing_deps", st.session_state.language))
    st.stop()

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = None
if 'subtitle_style' not in st.session_state:
    st.session_state.subtitle_style = "Classic"
if 'show_subtitles' not in st.session_state:
    st.session_state.show_subtitles = True
if 'vertical_format' not in st.session_state:
    st.session_state.vertical_format = True

# Main form
with st.form("extraction_form"):
    # URL input
    url = st.text_input(
        get_text("youtube_url", st.session_state.language),
        placeholder=get_text("url_placeholder", st.session_state.language),
        help=get_text("url_help", st.session_state.language)
    )
    
    # Two columns for options
    col1, col2 = st.columns(2)
    
    with col1:
        # Quality selector
        quality = st.selectbox(
            get_text("video_quality", st.session_state.language),
            options=["360p", "480p", "720p", "1080p"],
            index=2,  # Default to 720p
            help=get_text("quality_help", st.session_state.language)
        )
        
        # Number of clips
        num_clips = st.number_input(
            get_text("num_clips", st.session_state.language),
            min_value=1,
            max_value=10,
            value=DEFAULT_NUM_CLIPS,
            help=get_text("clips_help", st.session_state.language)
        )
    
    with col2:
        # Format checkbox
        vertical_format = st.checkbox(
            get_text("vertical_format", st.session_state.language),
            value=st.session_state.vertical_format,
            help=get_text("vertical_help", st.session_state.language),
            key="vertical_format_checkbox"
        )
        
        # Add subtitles
        add_subtitles = st.checkbox(
            get_text("add_subtitles", st.session_state.language),
            value=st.session_state.show_subtitles,
            help=get_text("subtitles_help", st.session_state.language),
            key="add_subtitles_checkbox"
        )
    
    # Submit button
    submitted = st.form_submit_button(get_text("extract_button", st.session_state.language), use_container_width=True)

# Update session state
if 'vertical_format_checkbox' in st.session_state:
    st.session_state.vertical_format = st.session_state.vertical_format_checkbox
if 'add_subtitles_checkbox' in st.session_state:
    st.session_state.show_subtitles = st.session_state.add_subtitles_checkbox

# Subtitle style selector (outside form for dynamic updates)
if st.session_state.show_subtitles:
    st.divider()
    st.subheader(get_text("subtitle_style_header", st.session_state.language))
    
    # Create style preview with translations
    style_options = list(SUBTITLE_TEMPLATES.keys())
    
    # Get translated style descriptions
    def get_style_description(style_name):
        style_key = f"style_{style_name.lower().replace(' ', '_')}"
        return get_text(style_key, st.session_state.language)
    
    subtitle_style = st.selectbox(
        get_text("choose_style", st.session_state.language),
        options=style_options,
        format_func=lambda x: f"{x} - {get_style_description(x)}",
        help=get_text("style_help", st.session_state.language),
        index=style_options.index(st.session_state.subtitle_style),
        key="subtitle_style_selector"
    )
    
    # Update session state
    st.session_state.subtitle_style = subtitle_style
    
    # Show style preview - this will update dynamically
    selected_template = SUBTITLE_TEMPLATES[subtitle_style]
    col1, col2 = st.columns(2)
    
    # Use the vertical format from session state
    format_type = "vertical" if st.session_state.vertical_format else "horizontal"
    settings = selected_template[format_type]
    
    with col1:
        st.caption(get_text("style_preview", st.session_state.language))
        st.markdown(f"""
        <div style="color: black;">
            • {get_text("font_size", st.session_state.language, size=settings['fontsize'])}<br>
            • {get_text("position", st.session_state.language, percent=int(settings['position'] * 100))}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.caption(get_text("colors", st.session_state.language))
        # Create color preview boxes using HTML
        color_html = f"""
        <div style="display: flex; gap: 10px; align-items: center; color: black;">
            <div style="width: 30px; height: 30px; background-color: rgb{settings['color']}; border: 1px solid black;"></div>
            <span style="color: black;">{get_text("text_color", st.session_state.language)}</span>
            <div style="width: 30px; height: 30px; background-color: rgb{settings['stroke_color']}; border: 1px solid black;"></div>
            <span style="color: black;">{get_text("outline_color", st.session_state.language)}</span>
        </div>
        """
        st.markdown(color_html, unsafe_allow_html=True)

# Process the video
if submitted and url:
    st.session_state.processing = True
    
    try:
        # Create a container for progress updates
        progress_container = st.container()
        
        with progress_container:
            # Step 1: Download
            with st.spinner("📥 Downloading video..."):
                downloader = YouTubeDownloader()
                video_metadata = downloader.download(url, quality)
                video_path = video_metadata['filepath']
                st.success(f"✅ Downloaded: {video_metadata['title']}")
            
            # Step 2: Transcribe
            with st.spinner(get_text("transcribing", st.session_state.language)):
                progress_bar = st.progress(0)
                transcriber = VideoTranscriber()
                # Pass language code to Whisper (fr for French, en for English)
                whisper_lang = 'fr' if st.session_state.language == 'fr' else 'en'
                transcript = transcriber.transcribe(video_path, language=whisper_lang)
                progress_bar.progress(100)
                st.success(get_text("transcribed", st.session_state.language, segments=len(transcript['segments'])))
            
            # Step 3: Analyze
            with st.spinner("🤖 Analyzing for viral moments..."):
                analyzer = ViralMomentAnalyzer()
                viral_moments = analyzer.analyze_transcript(transcript)
                
                if not viral_moments:
                    st.error("No viral moments found. Try a different video.")
                    st.stop()
                
                st.success(f"✅ Found {len(viral_moments)} viral moments!")
            
            # Step 4: Show moments and let user select
            st.subheader("📊 Viral Moments Found")
            
            selected_indices = []
            for i, moment in enumerate(viral_moments[:num_clips]):
                col1, col2, col3 = st.columns([1, 2, 3])
                with col1:
                    if st.checkbox(f"Clip {i+1}", value=True, key=f"moment_{i}"):
                        selected_indices.append(i)
                with col2:
                    st.write(f"⏱️ {format_time(moment['start'])} - {format_time(moment['end'])}")
                with col3:
                    st.write(f"Score: {moment['score']:.1f}/10")
                st.caption(f"💬 {moment['reason']}")
                st.divider()
            
            if not selected_indices:
                st.warning("Please select at least one moment to process.")
                st.stop()
            
            # Step 5: Extract clips
            selected_moments = [viral_moments[i] for i in selected_indices]
            
            with st.spinner(f"✂️ Extracting {len(selected_moments)} clips..."):
                processor = VideoProcessor()
                refined_moments = analyzer.refine_moments(selected_moments, transcript)
                validated_moments = processor.validate_timestamps(video_path, refined_moments)
                
                clip_paths = []
                progress_bar = st.progress(0)
                
                for i, moment in enumerate(validated_moments):
                    output_name = f"viral_clip_{i+1}_score_{moment['score']:.1f}"
                    clip_path = processor.extract_clip(
                        video_path,
                        moment['start'],
                        moment['end'],
                        output_name,
                        vertical_format=vertical_format
                    )
                    clip_paths.append(clip_path)
                    
                    # Save metadata
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
                    
                    progress_bar.progress((i + 1) / len(validated_moments))
                
                st.success(f"✅ Extracted {len(clip_paths)} clips!")
            
            # Step 5.5: Preview and adjust clips (optional)
            st.divider()
            st.subheader("✂️ Preview & Adjust Clips")
            st.info("Preview your clips and fine-tune the start/end times if needed")
            
            adjusted_clips = []
            adjustments_made = False
            
            for i, (clip_path, moment) in enumerate(zip(clip_paths, validated_moments)):
                with st.expander(f"📹 Clip {i+1} - Score: {moment['score']:.1f}/10", expanded=(i==0)):
                    # Display the video
                    st.video(clip_path)
                    
                    # Get video info
                    video_info = processor.get_video_info(video_path)
                    max_duration = video_info['duration']
                    
                    # Time adjustment controls
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        # Start time adjustment
                        new_start = st.number_input(
                            "Start time (seconds)",
                            min_value=0.0,
                            max_value=max_duration,
                            value=float(moment['start']),
                            step=0.1,
                            format="%.1f",
                            key=f"start_time_{i}"
                        )
                    
                    with col2:
                        # End time adjustment
                        new_end = st.number_input(
                            "End time (seconds)",
                            min_value=0.0,
                            max_value=max_duration,
                            value=float(moment['end']),
                            step=0.1,
                            format="%.1f",
                            key=f"end_time_{i}"
                        )
                    
                    with col3:
                        # Show duration
                        duration = new_end - new_start
                        st.metric("Duration", f"{duration:.1f}s")
                    
                    # Check if adjustments were made
                    if new_start != moment['start'] or new_end != moment['end']:
                        adjustments_made = True
                        st.warning(f"⚠️ Adjusted: {format_time(new_start)} → {format_time(new_end)}")
                    
                    # Store adjusted values
                    adjusted_moment = moment.copy()
                    adjusted_moment['start'] = new_start
                    adjusted_moment['end'] = new_end
                    adjusted_moment['duration'] = new_end - new_start
                    adjusted_clips.append((clip_path, adjusted_moment))
            
            # Re-extract clips if adjustments were made
            if adjustments_made:
                if st.button("🔄 Apply Adjustments & Re-extract Clips", type="primary"):
                    with st.spinner("Re-extracting clips with new timings..."):
                        new_clip_paths = []
                        progress_bar = st.progress(0)
                        
                        for i, (old_clip_path, adj_moment) in enumerate(adjusted_clips):
                            output_name = f"viral_clip_{i+1}_score_{adj_moment['score']:.1f}_adjusted"
                            new_clip_path = processor.extract_clip(
                                video_path,
                                adj_moment['start'],
                                adj_moment['end'],
                                output_name,
                                vertical_format=vertical_format
                            )
                            new_clip_paths.append(new_clip_path)
                            
                            # Update metadata
                            metadata_path = Path(new_clip_path).with_suffix('.json')
                            with open(metadata_path, 'w') as f:
                                json.dump({
                                    'original_video': str(video_path),
                                    'start_time': adj_moment['start'],
                                    'end_time': adj_moment['end'],
                                    'duration': adj_moment['duration'],
                                    'score': adj_moment['score'],
                                    'reason': adj_moment.get('reason', ''),
                                    'original_start': adj_moment.get('original_start', adj_moment['start']),
                                    'original_end': adj_moment.get('original_end', adj_moment['end'])
                                }, f, indent=2)
                            
                            progress_bar.progress((i + 1) / len(adjusted_clips))
                        
                        clip_paths = new_clip_paths
                        validated_moments = [adj[1] for adj in adjusted_clips]
                        st.success("✅ Clips re-extracted with adjusted timings!")
            
            # Step 6: Add subtitles
            final_clips = clip_paths
            if add_subtitles:
                with st.spinner("🎨 Adding subtitles..."):
                    generator = SubtitleGenerator()
                    subtitled_clips = []
                    progress_bar = st.progress(0)
                    
                    for i, clip_path in enumerate(clip_paths):
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
                                vertical_format=vertical_format,
                                clip_start_time=metadata['start_time'],
                                style_template=st.session_state.subtitle_style,
                                language=st.session_state.language
                            )
                            subtitled_clips.append(subtitled_path)
                        except Exception as e:
                            st.warning(f"Failed to add subtitles to clip {i+1}: {e}")
                            subtitled_clips.append(clip_path)
                        
                        progress_bar.progress((i + 1) / len(clip_paths))
                    
                    final_clips = subtitled_clips
                    st.success(f"✅ Added subtitles to {len(subtitled_clips)} clips!")
            
            # Show completion message
            st.balloons()
            st.success(get_text("processing_complete", st.session_state.language))
            
            # Store results in session state
            st.session_state.results = {
                'clips': final_clips,
                'metadata': video_metadata,
                'moments': validated_moments
            }
            
    except Exception as e:
        st.error(get_text("error", st.session_state.language, message=str(e)))
    finally:
        st.session_state.processing = False

# Display results if available (outside the processing block)
if st.session_state.results and not st.session_state.processing:
    st.divider()
    st.success(get_text("processing_complete", st.session_state.language))
    
    # Display download links
    st.subheader(get_text("download_header", st.session_state.language))
    
    # Create columns for better layout
    for i, clip_path in enumerate(st.session_state.results['clips']):
        clip_name = Path(clip_path).name
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Display clip info
            if i < len(st.session_state.results.get('moments', [])):
                moment = st.session_state.results['moments'][i]
                st.write(f"**{clip_name}**")
                st.caption(f"{get_text('score_label', st.session_state.language, score=moment['score'])} | {get_text('time_range', st.session_state.language, start=format_time(moment['start']), end=format_time(moment['end']))}")
        
        with col2:
            # Download button that doesn't reset the state
            with open(clip_path, 'rb') as f:
                clip_data = f.read()
            
            st.download_button(
                label=get_text("download_button", st.session_state.language, filename=clip_name),
                data=clip_data,
                file_name=clip_name,
                mime="video/mp4",
                key=f"persistent_download_{i}_{clip_name}"  # Unique key that persists
            )
    
    # Add a button to process a new video
    if st.button("🎬 " + ("Traiter une Nouvelle Vidéo" if st.session_state.language == 'fr' else "Process New Video")):
        st.session_state.results = None
        st.rerun()

# Footer
st.divider()
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 0.9em;">
{get_text("footer", st.session_state.language)}
</div>
""", unsafe_allow_html=True)