import streamlit as st
import json
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from modules.downloader import YouTubeDownloader
from modules.transcriber import VideoTranscriber
from modules.analyzer import ViralMomentAnalyzer
from modules.video_processor import VideoProcessor
from modules.subtitle_generator import SubtitleGenerator
from utils.helpers import check_dependencies, format_time
from config import DEFAULT_NUM_CLIPS, SUBTITLE_TEMPLATES, OPENAI_API_KEY, ANTHROPIC_API_KEY

# Page config
st.set_page_config(
    page_title="Viral Clips Extractor",
    page_icon="🎬",
    layout="centered"
)

# Clean, minimal CSS
st.markdown("""
<style>
    /* Clean white background */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Add spacing and structure */
    .block-container {
        padding: 2rem 1rem;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Main button - Extract Clips */
    .stButton > button {
        background-color: black !important;
        color: white !important;
        border: none !important;
        font-weight: 600;
        transition: all 0.3s;
        padding: 0.75rem 2rem !important;
        border-radius: 8px !important;
        margin-top: 1rem;
    }
    
    .stButton > button:hover {
        background-color: #1a1a1a !important;
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Ensure button text stays white */
    .stButton > button > div {
        color: white !important;
    }
    
    .stButton > button > div > p {
        color: white !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        border: 2px solid #e0e0e0;
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
        transition: border-color 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #666 !important;
        outline: none !important;
    }
    
    /* Select boxes */
    .stSelectbox > div > div > select {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ced4da;
    }
    
    /* Streamlit select box container */
    .stSelectbox > div > div {
        background-color: white !important;
    }
    
    /* Select box dropdown styling */
    .stSelectbox [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div > div {
        color: black !important;
    }
    
    /* Number inputs */
    .stNumberInput > div > div > input {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ced4da;
    }
    
    /* Number input label */
    .stNumberInput > label {
        color: black !important;
        font-weight: 400;
    }
    
    /* Number input container */
    .stNumberInput > div {
        background-color: transparent !important;
    }
    
    .stNumberInput input[type="number"] {
        background-color: white !important;
        color: black !important;
    }
    
    /* Checkbox labels */
    .stCheckbox > label {
        color: black !important;
    }
    
    /* Checkbox label text specifically */
    .stCheckbox label {
        color: black !important;
    }
    
    .stCheckbox > label > div > p {
        color: black !important;
    }
    
    /* Target the actual checkbox text span */
    .stCheckbox label span {
        color: black !important;
    }
    
    /* All form labels */
    .stTextInput > label,
    .stSelectbox > label,
    .stNumberInput > label,
    .stTextArea > label {
        color: black !important;
    }
    
    /* Streamlit's baseui components for select boxes */
    [data-baseweb="select"] {
        background-color: white !important;
    }
    
    [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
        border-color: #ced4da !important;
    }
    
    /* Select dropdown menu */
    [data-baseweb="menu"] {
        background-color: white !important;
    }
    
    [data-baseweb="menu"] li {
        color: black !important;
        background-color: white !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background-color: #f0f0f0 !important;
    }
    
    /* Force all form-related text to be black */
    .stNumberInput label p,
    .stCheckbox label p,
    .stSelectbox label p,
    .stTextInput label p {
        color: black !important;
    }
    
    /* Main title and text should be black */
    h1 {
        color: black !important;
    }
    
    /* Subheaders black */
    h2, h3, h4 {
        color: black !important;
    }
    
    /* Regular text paragraphs black */
    .stMarkdown p {
        color: black !important;
    }
    
    /* Progress text */
    .stText {
        color: black !important;
    }
    
    /* Hide progress bar */
    .stProgress {
        display: none !important;
    }
    
    /* Success/Error/Info messages */
    .stAlert {
        background-color: white !important;
        border: 1px solid #dee2e6 !important;
    }
    
    /* Info messages specifically - override blue background */
    .stAlert[data-baseweb="notification"] {
        background-color: white !important;
    }
    
    .stInfo {
        background-color: white !important;
        color: black !important;
    }
    
    .stInfo > div {
        background-color: white !important;
        color: black !important;
    }
    
    /* All alert text should be black */
    .stAlert p {
        color: black !important;
    }
    
    /* Metrics styling - ensure black text */
    [data-testid="metric-container"] {
        background-color: white !important;
    }
    
    [data-testid="metric-container"] > div {
        color: black !important;
    }
    
    /* Force metric text to be black */
    div[data-testid="stMetricValue"] {
        color: black !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: black !important;
    }
    
    /* Download button - green */
    .stDownloadButton > button {
        background-color: #22c55e !important;
        color: white !important;
        border: none !important;
        font-weight: 500;
        padding: 0.5rem 1.5rem;
        border-radius: 6px !important;
        font-size: 0.9rem !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: #16a34a !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
    }
    
    /* Process Another Video button - secondary style */
    .stButton > button[kind="secondary"] {
        background-color: #f3f4f6 !important;
        color: #374151 !important;
        border: 2px solid #d1d5db !important;
        font-weight: 500;
        padding: 0.75rem 2rem !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        margin: 0 auto;
        display: block;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #e5e7eb !important;
        border-color: #9ca3af !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Section styling */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stForm"]) {
        background-color: #fafafa;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e5e5e5;
        margin-bottom: 2rem;
    }
    
    /* Results section */
    div[data-testid="column"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        margin-bottom: 1rem;
    }
    
    /* Headers styling */
    h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }
    
    /* Caption styling */
    .caption {
        font-size: 0.875rem !important;
        color: #666 !important;
    }
    
    /* Divider styling */
    hr {
        margin: 2rem 0 !important;
        border: none !important;
        border-top: 1px solid #e5e5e5 !important;
    }
</style>
""", unsafe_allow_html=True)

# Check dependencies
if not check_dependencies():
    st.error("❌ Missing dependencies! Install FFmpeg and ensure Ollama is running: `ollama serve`")
    st.stop()

# Title with better spacing
st.title("Viral Clips Extractor")
st.markdown("Extract the most engaging moments from YouTube videos automatically using AI")

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'clips' not in st.session_state:
    st.session_state.clips = None
if 'video_info' not in st.session_state:
    st.session_state.video_info = None

# Main form with better organization
with st.form("extraction_form"):
    st.markdown("### Video Input")
    # URL and Quality
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...", label_visibility="visible")
    with col2:
        quality = st.selectbox("Quality", ["360p", "480p", "720p", "1080p"], index=2)
    
    st.markdown("### Processing Options")
    # Settings in 2 rows for better readability
    col1, col2 = st.columns(2)
    with col1:
        ai_provider = st.selectbox(
            "AI Provider",
            options=["ollama", "openai", "anthropic"],
            index=0,
            help="Ollama runs locally, OpenAI and Anthropic require API keys"
        )
        min_score = st.number_input(
            "Minimum Virality Score",
            min_value=0.0,
            max_value=10.0,
            value=7.0,
            step=0.5,
            help="Only extract clips with scores above this threshold"
        )
    
    with col2:
        vertical_format = st.checkbox("Vertical Format (9:16)", value=True, help="Optimized for TikTok, Reels, Shorts")
        add_subtitles = st.checkbox("Add Subtitles", value=True, help="Automatically generate styled subtitles")
        
        # Subtitle style (conditional)
        if add_subtitles:
            subtitle_style = st.selectbox(
                "Subtitle Style",
                options=list(SUBTITLE_TEMPLATES.keys()),
                index=3,  # TikTok Style
                help="Choose subtitle appearance"
            )
        else:
            subtitle_style = "TikTok Style"
    
    # Submit button with more spacing
    st.markdown("")
    submitted = st.form_submit_button("Extract Viral Clips", type="primary", use_container_width=True)

# Show API key warnings if needed
if ai_provider == "openai" and not OPENAI_API_KEY:
    st.warning("⚠️ OPENAI_API_KEY not set. Set it as environment variable or in .env file.")
elif ai_provider == "anthropic" and not ANTHROPIC_API_KEY:
    st.warning("⚠️ ANTHROPIC_API_KEY not set. Set it as environment variable or in .env file.")

# Process video when form is submitted
if submitted and url and not st.session_state.processing:
    st.session_state.processing = True
    
    try:
        # Progress container with better styling
        progress_container = st.container()
        with progress_container:
            progress_text = st.empty()
            
        # Step 1: Download
        progress_text.info("Step 1/4: Downloading video from YouTube...")
        downloader = YouTubeDownloader()
        video_data = downloader.download(url, quality)
        st.session_state.video_info = video_data
        
        # Step 2: Transcribe
        progress_text.info("Step 2/4: Transcribing audio...")
        transcriber = VideoTranscriber()
        transcript = transcriber.transcribe(video_data['filepath'], language=None)
        detected_language = transcript.get('language', 'en')
        
        # Step 3: Find viral moments
        progress_text.info("Step 3/4: Analyzing for viral moments...")
        analyzer = ViralMomentAnalyzer(provider=ai_provider)
        viral_moments = analyzer.analyze_transcript(transcript, chunk_duration=30)
        
        if not viral_moments:
            st.error("No viral moments found. Try a different video or lower the minimum score.")
            st.stop()
        
        # Filter by minimum score
        high_viral_moments = [m for m in viral_moments if m['score'] >= min_score]
        if not high_viral_moments:
            # If no moments meet the threshold, take top 3
            high_viral_moments = viral_moments[:3]
        
        # Step 4: Extract clips
        progress_text.info(f"Step 4/4: Extracting {len(high_viral_moments)} clips...")
        processor = VideoProcessor()
        
        # Refine and validate moments
        refined_moments = analyzer.refine_moments(high_viral_moments, transcript)
        validated_moments = processor.validate_timestamps(video_data['filepath'], refined_moments)
        
        # Thread-safe progress tracking
        progress_lock = threading.Lock()
        progress_tracker = {'completed_count': 0}
        
        def extract_single_clip(index, moment):
            # Extract clip
            output_name = f"clip_{index+1}_score_{moment['score']:.1f}"
            clip_path = processor.extract_clip(
                video_data['filepath'],
                moment['start'],
                moment['end'],
                output_name,
                vertical_format=vertical_format
            )
            
            # Add subtitles if requested
            if add_subtitles:
                generator = SubtitleGenerator()
                output_name = f"clip_{index+1}_final"
                clip_path = generator.add_subtitles(
                    clip_path,
                    transcript,
                    moment['start'],
                    moment['end'],
                    output_name,
                    vertical_format=vertical_format,
                    clip_start_time=moment['start'],
                    style_template=subtitle_style,
                    language=detected_language
                )
            
            # Update progress
            with progress_lock:
                progress_tracker['completed_count'] += 1
            
            return {
                'index': index,
                'path': clip_path,
                'start': moment['start'],
                'end': moment['end'],
                'score': moment['score'],
                'duration': moment['duration']
            }
        
        # Extract clips in parallel
        clips = []
        max_workers = min(4, len(validated_moments))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_clip = {
                executor.submit(extract_single_clip, i, moment): i 
                for i, moment in enumerate(validated_moments)
            }
            
            for future in as_completed(future_to_clip):
                try:
                    result = future.result()
                    clips.append(result)
                except Exception as e:
                    st.error(f"Failed to extract clip: {str(e)}")
        
        # Sort clips by index
        clips.sort(key=lambda x: x['index'])
        clips = [{k: v for k, v in clip.items() if k != 'index'} for clip in clips]
        
        # Clear progress and show success
        progress_text.empty()
        
        st.session_state.clips = clips
        st.success(f"Successfully extracted {len(clips)} viral clips!")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        st.session_state.processing = False

# Show results
if st.session_state.clips and st.session_state.video_info:
    st.divider()
    
    # Video info with cleaner formatting
    st.markdown(f"### Results")
    st.markdown(f"**Video:** {st.session_state.video_info['title']}")
    st.markdown(f"**Clips extracted:** {len(st.session_state.clips)}")
    
    # Clips in a clean grid with better styling
    st.markdown("---")
    cols = st.columns(2)
    for i, clip in enumerate(st.session_state.clips):
        with cols[i % 2]:
            # Card-like container for each clip
            st.markdown(f"#### Clip {i+1}")
            
            # Metrics in a clean format
            col_score, col_duration = st.columns(2)
            with col_score:
                st.metric("Virality Score", f"{clip['score']:.1f}/10")
            with col_duration:
                st.metric("Duration", f"{clip['duration']:.1f}s")
            
            # Download button
            with open(clip['path'], 'rb') as f:
                st.download_button(
                    label="Download Clip",
                    data=f.read(),
                    file_name=Path(clip['path']).name,
                    mime="video/mp4",
                    key=f"dl_{i}",
                    use_container_width=True
                )
            
            # Add spacing between clips
            st.markdown("")
    
    # Process another video - better design
    st.markdown("---")
    st.markdown("")  # Add some spacing
    
    # Create a container for the button with custom styling
    button_container = st.container()
    with button_container:
        if st.button("🎬 Process Another Video", use_container_width=False, type="secondary"):
            st.session_state.clips = None
            st.session_state.video_info = None
            st.rerun()