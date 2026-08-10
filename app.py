import os
import time
import tempfile
import yt_dlp
import streamlit as st
from google import genai

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="InstaReel AI Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TITLE & HEADER ---
st.title("🎬 Instagram Reel AI Analyzer")
st.caption("Paste a public Instagram Reel link to summarize content, ask custom prompts, extract links, or download the video.")

# --- SIDEBAR FOR API KEY & ABOUT ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Secure API Key Handling (Secrets -> Env -> Manual Input)
    default_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            default_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    if not default_key and os.getenv("GEMINI_API_KEY"):
        default_key = os.getenv("GEMINI_API_KEY")
        
    api_key_input = st.text_input(
        "Gemini API Key",
        value=default_key,
        type="password",
        help="Reads from secrets/env or enter manually here."
    )
    
    st.divider()
    st.markdown("""
    ### 📌 Tips
    - **Default Mode**: Concise summary for quick reading.
    - **Links**: Spoken or visual links are extracted automatically.
    - **Downloads**: Download the Reel video directly as `.mp4`.
    """)

# Active API Key
api_key = api_key_input.strip()

# --- HELPER FUNCTIONS ---
def download_reel(url):
    """Downloads an Instagram Reel as an MP4 file to a temporary location"""
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"reel_{int(time.time())}.mp4")
    
    ydl_opts = {
        'format': 'mp4/bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'overwrites': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            st.error("Failed to save downloaded video file.")
            return None
    except Exception as e:
        st.error(f"Error downloading Reel: {e}")
        return None

def build_prompt(mode, custom_prompt_text):
    """Builds the AI prompt based on selected mode and options"""
    link_instruction = "\n\nCRITICAL: If any website links, URLs, social handles, or reference links are spoken or displayed as text overlays in the video, explicitly list them clearly at the end under a '🔗 Links & References' section."
    
    if mode == "⚡ Concise Summary":
        return (
            "Provide a concise, engaging summary of this Instagram Reel in 2-3 short paragraphs. "
            "Focus on the core idea, key takeaways, and main content. "
            "Do NOT use rigid step-by-step numbers or numbered bullet lists."
            + link_instruction
        )
    elif mode == "🔍 Detailed Breakdown":
        return (
            "Analyze this Instagram Reel thoroughly and provide a structured breakdown:\n"
            "1. THE HOOK: What happens/is said in the first 3 seconds?\n"
            "2. VISUALS: Describe text overlays, settings, visual transitions, and physical actions.\n"
            "3. AUDIO: Summarize spoken words, music context, or dialogue accurately.\n"
            "4. CORE POINT: What is the ultimate takeaway?\n"
            "Be specific and detailed."
            + link_instruction
        )
    elif mode == "✨ Custom Prompt":
        base_prompt = custom_prompt_text.strip() if custom_prompt_text.strip() else "Summarize the key points of this Reel."
        return base_prompt + link_instruction
    return "Summarize this Instagram Reel." + link_instruction

def analyze_video_with_ai(video_path, prompt, client):
    """Uploads video to Gemini API, polls processing, and generates content response"""
    status_box = st.empty()
    status_box.info("📤 Uploading video to AI server...")
    
    try:
        video_file = client.files.upload(file=video_path)
        
        status_box.info("⏳ AI is processing video content...")
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
            
        if video_file.state.name == "FAILED":
            status_box.error(f"Video processing failed: {video_file.error.message}")
            return None
            
        status_box.info("🤖 AI is analyzing your Reel...")
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[video_file, prompt]
        )
        
        status_box.empty()
        return response.text
    except Exception as e:
        status_box.error(f"AI Analysis error: {e}")
        return None

# --- MAIN INPUT SECTION ---
input_container = st.container(border=True)

with input_container:
    col_url, col_paste, col_btn = st.columns([3.2, 1.1, 1.2], vertical_alignment="bottom")
    
    with col_url:
        reel_url = st.text_input(
            "Instagram Reel URL:",
            placeholder="https://www.instagram.com/reel/...",
            label_visibility="visible"
        )
        
    with col_paste:
        st.components.v1.html(
            """
            <div style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; margin-top: 4px;">
                <button id="paste-btn" style="
                    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                    color: white;
                    border: none;
                    padding: 9px 14px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    font-size: 14px;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                    transition: all 0.2s ease;
                ">
                    📋 Paste Link
                </button>
            </div>
            <script>
            document.getElementById('paste-btn').addEventListener('click', async () => {
                try {
                    const text = await navigator.clipboard.readText();
                    if (text) {
                        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                        let targetInput = null;
                        inputs.forEach(input => {
                            if (input.placeholder && input.placeholder.includes('instagram.com')) {
                                targetInput = input;
                            }
                        });
                        if (!targetInput && inputs.length > 0) {
                            targetInput = inputs[0];
                        }
                        if (targetInput) {
                            targetInput.focus();
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(targetInput, text);
                            targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                            targetInput.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                } catch (err) {
                    alert('Clipboard access denied or restricted by browser. Please allow clipboard permissions or paste manually (Ctrl+V / Cmd+V).');
                }
            });
            </script>
            """,
            height=45
        )
        
    with col_btn:
        analyze_btn = st.button("🚀 Analyze Reel", type="primary", width="stretch")

    # Compact Collapsible Options (does not clutter standard usage)
    with st.expander("🎛️ Customize Analysis Style & Prompts", expanded=False):
        analysis_mode = st.segmented_control(
            "Analysis Style:",
            options=["⚡ Concise Summary", "🔍 Detailed Breakdown", "✨ Custom Prompt"],
            default="⚡ Concise Summary"
        )
        
        custom_prompt_val = ""
        if analysis_mode == "✨ Custom Prompt":
            custom_prompt_val = st.text_area(
                "Your Custom AI Prompt:",
                placeholder="e.g. List all recipe ingredients with exact measurements mentioned in this video...",
                help="Type any custom instruction or question about the Reel."
            )
        else:
            custom_prompt_val = ""

# --- PROCESSING TRIGGER ---
if analyze_btn:
    if not api_key:
        st.error("⚠️ Gemini API key is missing. Please enter it in the sidebar settings.")
    elif not reel_url.strip():
        st.warning("⚠️ Please enter a valid Instagram Reel URL.")
    else:
        with st.spinner("Downloading Reel video..."):
            file_path = download_reel(reel_url.strip())
            
        if file_path and os.path.exists(file_path):
            st.session_state["current_video_path"] = file_path
            st.session_state["current_url"] = reel_url
            
            # Analyze with Gemini
            try:
                client = genai.Client(api_key=api_key)
                selected_mode = analysis_mode if analysis_mode else "⚡ Concise Summary"
                prompt_to_use = build_prompt(selected_mode, custom_prompt_val)
                
                with st.spinner("Running AI analysis..."):
                    result_text = analyze_video_with_ai(file_path, prompt_to_use, client)
                    st.session_state["analysis_result"] = result_text
            except Exception as ex:
                st.error(f"Initialization error: {ex}")

# --- DISPLAY RESULTS ---
if "current_video_path" in st.session_state and os.path.exists(st.session_state["current_video_path"]):
    video_path = st.session_state["current_video_path"]
    
    st.divider()
    res_col1, res_col2 = st.columns([1, 1])
    
    with res_col1:
        with st.container(border=True):
            st.subheader("📹 Reel Preview & Download")
            st.video(video_path)
            
            with open(video_path, "rb") as vf:
                video_bytes = vf.read()
                
            st.download_button(
                label="⬇️ Download Reel (.mp4)",
                data=video_bytes,
                file_name="instagram_reel.mp4",
                mime="video/mp4",
                width="stretch"
            )

    with res_col2:
        with st.container(border=True):
            st.subheader("📝 AI Insights")
            if "analysis_result" in st.session_state and st.session_state["analysis_result"]:
                st.markdown(st.session_state["analysis_result"])
            else:
                st.info("Click 'Analyze Reel' to view AI analysis.")
