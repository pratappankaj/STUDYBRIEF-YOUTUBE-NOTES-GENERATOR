from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import requests
import re
from google.genai import Client

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURATION
# ==========================================
GENAI_API_KEY = "AIzaSyD39QQnF5XaMQzQC6_hjZck1wN3GD2iLxc"
client = Client(api_key=GENAI_API_KEY)

def clean_vtt(vtt_text):
    """Removes VTT timestamps and metadata to leave only clean text."""
    lines = vtt_text.splitlines()
    clean_lines = []
    for line in lines:
        if any(x in line for x in ["WEBVTT", "Kind:", "Language:", "-->"]):
            continue
        if not line.strip():
            continue
        # Remove timestamps and HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        clean_lines.append(line.strip())
    
    final_text = []
    for i in range(len(clean_lines)):
        if i == 0 or (i > 0 and clean_lines[i] != clean_lines[i-1]):
            final_text.append(clean_lines[i])
            
    return " ".join(final_text)

@app.route("/generate-notes", methods=["POST"])
def generate_notes():
    data = request.get_json()
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'ignore_no_formats_error': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Metadata
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video Lecture')
            
            # 2. Extract Transcript
            transcript_text = ""
            subtitles = info.get('requested_subtitles')
            
            if subtitles and 'en' in subtitles:
                sub_url = subtitles['en']['url']
                response = requests.get(sub_url)
                if response.status_code == 200:
                    transcript_text = clean_vtt(response.text)
            
            if not transcript_text:
                transcript_text = info.get('description', '')

            if not transcript_text or len(transcript_text) < 50:
                return jsonify({"success": False, "error": "No sufficient transcript found."}), 500

            # 3. AI Generation using the stable 2.5 Flash-Lite (High Quota)
            prompt = f"""
            You are a professional academic note-taker. 
            Analyze this transcript for the video: "{title}".
            
            Format your response in CLEAN HTML (use <h3>, <p>, <ul>, <li>).
            Include:
            1. Executive Summary (Overview of the lecture)
            2. Core Concepts (Key terms and meanings)
            3. Detailed Analysis (The "meat" of the lecture)
            4. Conclusion/Summary

            Transcript content: {transcript_text[:12000]}
            """

            # CHANGE: We are now using gemini-2.5-flash-lite for stable free access
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", 
                contents=prompt
            )
            
            # Remove Markdown code blocks if the AI includes them
            raw_text = response.text
            final_notes = re.sub(r'```html|```', '', raw_text).strip()

            return jsonify({
                "success": True,
                "title": title,
                "notes": final_notes,
                "thumbnail": info.get('thumbnail')
            })

    except Exception as e:
        # Better error reporting for the UI
        error_msg = str(e)
        if "429" in error_msg:
            error_msg = "Free Tier Quota reached. Please try again in 60 seconds."
        return jsonify({"success": False, "error": error_msg}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)