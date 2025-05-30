import streamlit as st
from dotenv import load_dotenv
import os
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

import time
from google.api_core.exceptions import ResourceExhausted


# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check API Key
if not GOOGLE_API_KEY:
    st.error("❌ Google API Key not found. Please set 'GOOGLE_API_KEY' in your .env file.")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Prompt template
PROMPT = """You are an expert summarizer. Summarize the following YouTube transcript into well-structured and detailed notes with bullet points, key takeaways, and simplified language:\n\n"""

# Extract video ID from various YouTube URL formats
def get_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid YouTube URL")

# Get available transcript languages for a video
def get_available_languages(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        langs = [t.language_code for t in transcripts]
        return langs
    except Exception as e:
        st.error(f"Error fetching available transcript languages: {e}")
        return []

# Extract transcript text in given language
def extract_transcript_details(video_id, lang='en'):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        transcript = " ".join([item["text"] for item in transcript_list])
        return transcript
    except Exception as e:
        st.error(f"⚠️ Error fetching transcript: {e}")
        return None

# Generate Gemini summary
def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-1.5-pro-002")
    max_retries = 3
    retry_delay_sec = 60

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt + transcript_text)
            return response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                st.warning(f"Quota exceeded, retrying in {retry_delay_sec} seconds...")
                time.sleep(retry_delay_sec)
            else:
                st.error("Quota exceeded. Please check your Google Cloud billing and quota.")
                raise e

# Streamlit UI
st.title("🎬 YouTube Video → 📘 Detailed Notes")

yt_link = st.text_input("🔗 Enter YouTube Link:")

video_id = None
if yt_link:
    try:
        video_id = get_video_id(yt_link)
        st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)
    except Exception as e:
        st.error(f"❌ {e}")

if video_id:
    available_langs = get_available_languages(video_id)
    if available_langs:
        default_lang = 'en' if 'en' in available_langs else available_langs[0]
        lang_choice = st.selectbox("Select transcript language", available_langs, index=available_langs.index(default_lang))
    else:
        st.warning("No transcripts available for this video.")
        lang_choice = None

    if st.button("📝 Get Notes"):
        if lang_choice:
            with st.spinner("⏳ Fetching transcript and generating notes..."):
                transcript_text = extract_transcript_details(video_id, lang_choice)

                if transcript_text:
                    summary = generate_gemini_content(transcript_text, PROMPT)
                    st.success("✅ Notes generated successfully!")
                    st.markdown("### 🧾 Detailed Notes")
                    st.write(summary)
                else:
                    st.warning("⚠️ No transcript available or error occurred.")
        else:
            st.warning("Please select a transcript language.")
