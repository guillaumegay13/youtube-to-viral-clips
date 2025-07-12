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
        "clips_reextracted": "✅ Clips re-extracted with adjusted timings!",
        "clips_ready": "✅ Clips Ready",
        "clips_ready_desc": "Your clips are ready. Click below to add subtitles.",
        "proceed_subtitles": "🎨 Proceed to Add Subtitles",
        "adjust_timing": "**Adjust clip timing:**",
        
        # New workflow translations
        "step_download": "Download Video",
        "step_transcribe": "Transcribe",
        "step_analyze": "Find Viral Moments",
        "step_preview": "Preview & Adjust",
        "step_export": "Export",
        "download_video": "Download Video",
        "start_transcription": "Start Transcription",
        "analyze_info": "AI will analyze the transcript to find the most engaging moments",
        "find_viral_moments": "Find Viral Moments",
        "viral_clips_found": "Viral Clips Found",
        "clip_selection": "Select Clips",
        "timing_adjustment": "Adjust Timing",
        "viral_score": "Viral Score",
        "adjust_timing_info": "Select clips first, then adjust their timing",
        "extract_selected_clips": "Extract Selected Clips",
        "extracting_clips": "Extracting clips...",
        "clips_extracted": "Clips extracted successfully!",
        "adjust_clip_timing": "Adjust Clip Timing",
        "proceed_to_export": "Proceed to Export",
        "select_clips_first": "Please select clips first",
        "export_final_clips": "Export Final Clips",
        "processing_final_clips": "Processing final clips...",
        "prepare_all_downloads": "Prepare All Downloads",
        "download_individually": "Please download clips individually",
        "download": "Download",
        "process_new_video": "Process New Video"
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
        "position": "Position : {percent}% du haut",
        
        # Preview section
        "preview_header": "✂️ Aperçu et Ajustement des Clips",
        "preview_info": "Prévisualisez vos clips et ajustez les temps de début/fin si nécessaire",
        "clip_preview": "📹 Clip {num} - Score : {score}/10",
        "start_time": "Temps de début (secondes)",
        "end_time": "Temps de fin (secondes)",
        "duration": "Durée",
        "adjusted_warning": "⚠️ Ajusté : {start} → {end}",
        "apply_adjustments": "🔄 Appliquer les Ajustements et Ré-extraire",
        "reextracting": "Ré-extraction des clips avec les nouveaux timings...",
        "clips_reextracted": "✅ Clips ré-extraits avec les timings ajustés !",
        "clips_ready": "✅ Clips Prêts",
        "clips_ready_desc": "Vos clips sont prêts. Cliquez ci-dessous pour ajouter des sous-titres.",
        "proceed_subtitles": "🎨 Procéder à l'Ajout des Sous-titres",
        "adjust_timing": "**Ajuster le timing du clip :**",
        
        # New workflow translations
        "step_download": "Télécharger la Vidéo",
        "step_transcribe": "Transcrire",
        "step_analyze": "Trouver les Moments Viraux",
        "step_preview": "Aperçu et Ajustement",
        "step_export": "Exporter",
        "download_video": "Télécharger la Vidéo",
        "start_transcription": "Démarrer la Transcription",
        "analyze_info": "L'IA analysera la transcription pour trouver les moments les plus engageants",
        "find_viral_moments": "Trouver les Moments Viraux",
        "viral_clips_found": "Clips Viraux Trouvés",
        "clip_selection": "Sélectionner les Clips",
        "timing_adjustment": "Ajuster le Timing",
        "viral_score": "Score Viral",
        "adjust_timing_info": "Sélectionnez d'abord les clips, puis ajustez leur timing",
        "extract_selected_clips": "Extraire les Clips Sélectionnés",
        "extracting_clips": "Extraction des clips...",
        "clips_extracted": "Clips extraits avec succès !",
        "adjust_clip_timing": "Ajuster le Timing des Clips",
        "proceed_to_export": "Procéder à l'Export",
        "select_clips_first": "Veuillez d'abord sélectionner des clips",
        "export_final_clips": "Exporter les Clips Finaux",
        "processing_final_clips": "Traitement des clips finaux...",
        "prepare_all_downloads": "Préparer Tous les Téléchargements",
        "download_individually": "Veuillez télécharger les clips individuellement",
        "download": "Télécharger",
        "process_new_video": "Traiter une Nouvelle Vidéo"
    }
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text with optional formatting"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text