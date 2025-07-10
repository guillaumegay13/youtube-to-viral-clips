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
from config import DEFAULT_NUM_CLIPS, OUTPUTS_DIR, SUBTITLE_TEMPLATES

# Page config
st.set_page_config(
    page_title="YouTube Viral Clips Extractor",
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

# Title
st.title("🎬 YouTube Viral Clips Extractor")
st.markdown("Extract viral moments from YouTube videos with AI-generated subtitles")

# Check dependencies
if not check_dependencies():
    st.error("Missing dependencies! Please install FFmpeg and ensure Ollama is running.")
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
        "YouTube URL",
        placeholder="https://youtube.com/watch?v=...",
        help="Paste the YouTube video URL here"
    )
    
    # Two columns for options
    col1, col2 = st.columns(2)
    
    with col1:
        # Quality selector
        quality = st.selectbox(
            "Video Quality",
            options=["360p", "480p", "720p", "1080p"],
            index=2,  # Default to 720p
            help="Higher quality = larger file size"
        )
        
        # Number of clips
        num_clips = st.number_input(
            "Number of Clips",
            min_value=1,
            max_value=10,
            value=DEFAULT_NUM_CLIPS,
            help="Maximum number of viral clips to extract"
        )
    
    with col2:
        # Format checkbox
        vertical_format = st.checkbox(
            "Vertical Format (9:16)",
            value=st.session_state.vertical_format,
            help="Perfect for TikTok, Instagram Reels, YouTube Shorts",
            key="vertical_format_checkbox"
        )
        
        # Add subtitles
        add_subtitles = st.checkbox(
            "Add Subtitles",
            value=st.session_state.show_subtitles,
            help="Add animated word-by-word subtitles",
            key="add_subtitles_checkbox"
        )
    
    # Submit button
    submitted = st.form_submit_button("🚀 Extract Viral Clips", use_container_width=True)

# Update session state
if 'vertical_format_checkbox' in st.session_state:
    st.session_state.vertical_format = st.session_state.vertical_format_checkbox
if 'add_subtitles_checkbox' in st.session_state:
    st.session_state.show_subtitles = st.session_state.add_subtitles_checkbox

# Subtitle style selector (outside form for dynamic updates)
if st.session_state.show_subtitles:
    st.divider()
    st.subheader("Subtitle Style")
    
    # Create style preview
    style_options = list(SUBTITLE_TEMPLATES.keys())
    
    subtitle_style = st.selectbox(
        "Choose Style",
        options=style_options,
        format_func=lambda x: f"{x} - {SUBTITLE_TEMPLATES[x]['description']}",
        help="Select a subtitle style template",
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
        st.caption("Style Preview:")
        st.markdown(f"""
        <div style="color: black;">
            • Font Size: {settings['fontsize']}px<br>
            • Position: {int(settings['position'] * 100)}% from top
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.caption("Colors:")
        # Create color preview boxes using HTML
        color_html = f"""
        <div style="display: flex; gap: 10px; align-items: center; color: black;">
            <div style="width: 30px; height: 30px; background-color: rgb{settings['color']}; border: 1px solid black;"></div>
            <span style="color: black;">Text</span>
            <div style="width: 30px; height: 30px; background-color: rgb{settings['stroke_color']}; border: 1px solid black;"></div>
            <span style="color: black;">Outline</span>
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
            with st.spinner("🎧 Transcribing audio..."):
                progress_bar = st.progress(0)
                transcriber = VideoTranscriber()
                transcript = transcriber.transcribe(video_path)
                progress_bar.progress(100)
                st.success(f"✅ Transcribed: {len(transcript['segments'])} segments")
            
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
                                style_template=st.session_state.subtitle_style
                            )
                            subtitled_clips.append(subtitled_path)
                        except Exception as e:
                            st.warning(f"Failed to add subtitles to clip {i+1}: {e}")
                            subtitled_clips.append(clip_path)
                        
                        progress_bar.progress((i + 1) / len(clip_paths))
                    
                    final_clips = subtitled_clips
                    st.success(f"✅ Added subtitles to {len(subtitled_clips)} clips!")
            
            # Show results
            st.balloons()
            st.success("🎉 Processing complete!")
            
            # Display download links
            st.subheader("📥 Download Your Clips")
            
            for i, clip_path in enumerate(final_clips):
                clip_name = Path(clip_path).name
                with open(clip_path, 'rb') as f:
                    st.download_button(
                        label=f"⬇️ Download {clip_name}",
                        data=f.read(),
                        file_name=clip_name,
                        mime="video/mp4",
                        key=f"download_{i}"
                    )
            
            # Store results in session state
            st.session_state.results = {
                'clips': final_clips,
                'metadata': video_metadata
            }
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    finally:
        st.session_state.processing = False

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
Made with ❤️ using OpenAI Whisper, Ollama, and FFmpeg<br>
Ensure Ollama is running: <code>ollama serve</code>
</div>
""", unsafe_allow_html=True)