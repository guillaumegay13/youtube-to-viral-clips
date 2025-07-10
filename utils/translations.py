"""
Translation strings for the application
"""

TRANSLATIONS = {
    "en": {
        # Page title and header
        "page_title": "YouTube Viral Clips Extractor",
        "app_title": "🎬 YouTube Viral Clips Extractor",
        "app_subtitle": "Extract viral moments from YouTube videos with AI-generated subtitles",
        
        # Form labels
        "youtube_url": "YouTube URL",
        "url_placeholder": "https://youtube.com/watch?v=...",
        "url_help": "Paste the YouTube video URL here",
        "video_quality": "Video Quality",
        "quality_help": "Higher quality = larger file size",
        "num_clips": "Number of Clips",
        "clips_help": "Maximum number of viral clips to extract",
        "vertical_format": "Vertical Format (9:16)",
        "vertical_help": "Perfect for TikTok, Instagram Reels, YouTube Shorts",
        "add_subtitles": "Add Subtitles",
        "subtitles_help": "Add animated word-by-word subtitles",
        "extract_button": "🚀 Extract Viral Clips",
        
        # Subtitle style section
        "subtitle_style_header": "Subtitle Style",
        "choose_style": "Choose Style",
        "style_help": "Select a subtitle style template",
        "style_preview": "Style Preview:",
        "colors": "Colors:",
        "text_color": "Text",
        "outline_color": "Outline",
        
        # Progress messages
        "downloading": "📥 Downloading video...",
        "downloaded": "✅ Downloaded: {title}",
        "transcribing": "🎧 Transcribing audio...",
        "transcribed": "✅ Transcribed: {segments} segments",
        "analyzing": "🤖 Analyzing for viral moments...",
        "found_moments": "✅ Found {count} viral moments!",
        "no_moments": "No viral moments found. Try a different video.",
        "extracting_clips": "✂️ Extracting {count} clips...",
        "extracted_clips": "✅ Extracted {count} clips successfully!",
        "adding_subtitles": "🎨 Adding subtitles...",
        "added_subtitles": "✅ Added subtitles to {count} clips!",
        "processing_complete": "🎉 Processing complete!",
        
        # Viral moments section
        "viral_moments_header": "📊 Viral Moments Found",
        "clip_label": "Clip {num}",
        "score_label": "Score: {score}/10",
        "time_range": "{start} - {end}",
        "select_warning": "Please select at least one moment to process.",
        
        # Download section
        "download_header": "📥 Download Your Clips",
        "download_button": "⬇️ Download {filename}",
        
        # Errors
        "missing_deps": "Missing dependencies! Please install FFmpeg and ensure Ollama is running.",
        "error": "❌ Error: {message}",
        "failed_extract": "⚠️ Failed to extract clip {num}: {error}",
        "failed_subtitles": "Failed to add subtitles to clip {num}: {error}",
        
        # Footer
        "footer": "Made with ❤️ using OpenAI Whisper, Ollama, and FFmpeg<br>Ensure Ollama is running: <code>ollama serve</code>",
        
        # Style descriptions
        "style_classic": "White text with black outline",
        "style_bold_yellow": "Yellow text with thick black outline",
        "style_minimal": "Small white text with thin outline",
        "style_tiktok": "Large white text with red/blue shadow",
        "style_neon": "Cyan text with purple glow",
        
        # Units
        "font_size": "Font Size: {size}px",
        "position": "Position: {percent}% from top",
        
        # Preview section
        "preview_header": "✂️ Preview & Adjust Clips",
        "preview_info": "Preview your clips and fine-tune the start/end times if needed",
        "clip_preview": "📹 Clip {num} - Score: {score}/10",
        "start_time": "Start time (seconds)",
        "end_time": "End time (seconds)",
        "duration": "Duration",
        "adjusted_warning": "⚠️ Adjusted: {start} → {end}",
        "apply_adjustments": "🔄 Apply Adjustments & Re-extract Clips",
        "reextracting": "Re-extracting clips with new timings...",
        "clips_reextracted": "✅ Clips re-extracted with adjusted timings!"
    },
    
    "fr": {
        # Page title and header
        "page_title": "Extracteur de Clips Viraux YouTube",
        "app_title": "🎬 Extracteur de Clips Viraux YouTube",
        "app_subtitle": "Extrayez des moments viraux des vidéos YouTube avec des sous-titres générés par IA",
        
        # Form labels
        "youtube_url": "URL YouTube",
        "url_placeholder": "https://youtube.com/watch?v=...",
        "url_help": "Collez l'URL de la vidéo YouTube ici",
        "video_quality": "Qualité Vidéo",
        "quality_help": "Qualité supérieure = taille de fichier plus grande",
        "num_clips": "Nombre de Clips",
        "clips_help": "Nombre maximum de clips viraux à extraire",
        "vertical_format": "Format Vertical (9:16)",
        "vertical_help": "Parfait pour TikTok, Instagram Reels, YouTube Shorts",
        "add_subtitles": "Ajouter des Sous-titres",
        "subtitles_help": "Ajouter des sous-titres animés mot par mot",
        "extract_button": "🚀 Extraire les Clips Viraux",
        
        # Subtitle style section
        "subtitle_style_header": "Style des Sous-titres",
        "choose_style": "Choisir le Style",
        "style_help": "Sélectionnez un modèle de style de sous-titres",
        "style_preview": "Aperçu du Style :",
        "colors": "Couleurs :",
        "text_color": "Texte",
        "outline_color": "Contour",
        
        # Progress messages
        "downloading": "📥 Téléchargement de la vidéo...",
        "downloaded": "✅ Téléchargé : {title}",
        "transcribing": "🎧 Transcription de l'audio...",
        "transcribed": "✅ Transcrit : {segments} segments",
        "analyzing": "🤖 Analyse des moments viraux...",
        "found_moments": "✅ {count} moments viraux trouvés !",
        "no_moments": "Aucun moment viral trouvé. Essayez une autre vidéo.",
        "extracting_clips": "✂️ Extraction de {count} clips...",
        "extracted_clips": "✅ {count} clips extraits avec succès !",
        "adding_subtitles": "🎨 Ajout des sous-titres...",
        "added_subtitles": "✅ Sous-titres ajoutés à {count} clips !",
        "processing_complete": "🎉 Traitement terminé !",
        
        # Viral moments section
        "viral_moments_header": "📊 Moments Viraux Trouvés",
        "clip_label": "Clip {num}",
        "score_label": "Score : {score}/10",
        "time_range": "{start} - {end}",
        "select_warning": "Veuillez sélectionner au moins un moment à traiter.",
        
        # Download section
        "download_header": "📥 Télécharger Vos Clips",
        "download_button": "⬇️ Télécharger {filename}",
        
        # Errors
        "missing_deps": "Dépendances manquantes ! Veuillez installer FFmpeg et vous assurer qu'Ollama est en cours d'exécution.",
        "error": "❌ Erreur : {message}",
        "failed_extract": "⚠️ Échec de l'extraction du clip {num} : {error}",
        "failed_subtitles": "Échec de l'ajout des sous-titres au clip {num} : {error}",
        
        # Footer
        "footer": "Fait avec ❤️ en utilisant OpenAI Whisper, Ollama et FFmpeg<br>Assurez-vous qu'Ollama est en cours d'exécution : <code>ollama serve</code>",
        
        # Style descriptions
        "style_classic": "Texte blanc avec contour noir",
        "style_bold_yellow": "Texte jaune avec contour noir épais",
        "style_minimal": "Petit texte blanc avec contour fin",
        "style_tiktok": "Grand texte blanc avec ombre rouge/bleue",
        "style_neon": "Texte cyan avec lueur violette",
        
        # Units
        "font_size": "Taille de Police : {size}px",
        "position": "Position : {percent}% du haut"
    }
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text with optional formatting"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text