import os
import time
import yt_dlp
import streamlit as st
from google import genai

# --- PAGE SETUP ---
st.set_page_config(page_title="InstaReel AI Analyzer", page_icon="🧠", layout="centered")

st.title("🧠 Instagram Reel AI Analyzer")
st.write("Paste a public Instagram Reel link below to let AI watch, transcribe, and summarize the content.")

# --- SECURE API KEY ACCESS ---
# This safely reads the key from Streamlit's cloud panel (or local secrets)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ GEMINI_API_KEY missing from system settings.")
    st.stop()

# --- CORE FUNCTIONS ---
def download_reel(url):
    """Downloads the Instagram Reel smoothly as an MP4 file"""
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': 'web_downloaded_reel.mp4',
        'quiet': True,
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return "web_downloaded_reel.mp4"
    except Exception as e:
        st.error(f"Error downloading video: {e}")
        return None

def analyze_video_with_ai(video_path, client):
    """Uploads the video to Gemini and extracts insights"""
    video_file = client.files.upload(file=video_path)
    
    status_text = st.empty()
    status_text.info("⏳ Waiting for video processing to complete on AI servers...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        st.error(f"Video processing failed: {video_file.error.message}")
        return None
        
    status_text.success("🚀 AI Analysis initialized!")
    
    prompt = (
        "Analyze this Instagram Reel thoroughly and provide a structured breakdown:\n"
        "1. THE HOOK: What happens/is said in the first 3 seconds?\n"
        "2. VISUALS: Describe text overlays, settings, and physical actions.\n"
        "3. AUDIO: Summarize spoken words or dialogue accurately.\n"
        "4. CORE POINT: What is the ultimate takeaway?\n"
        "Be specific. Avoid vague summaries."
    )
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=[video_file, prompt]
    )
    
    if os.path.exists(video_path):
        os.remove(video_path)
        
    return response.text

# --- USER INTERFACE CONTROL FLOW ---
reel_url = st.text_input("Instagram Reel URL:", placeholder="https://instagram.com...")

if st.button("Analyze Reel", type="primary"):
    if not reel_url:
        st.warning("Please input a valid Instagram Reel URL.")
    else:
        with st.spinner("Processing... This takes a moment depending on the video length."):
            video_file = download_reel(reel_url)
            
            if video_file:
                client = genai.Client(api_key=api_key)
                ai_summary = analyze_video_with_ai(video_file, client)
                
                if ai_summary:
                    st.success("Analysis Complete!")
                    st.subheader("📝 AI Breakdown Summary")
                    st.markdown(ai_summary)
