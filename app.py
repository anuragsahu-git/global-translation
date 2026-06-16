import streamlit as st
import streamlit.components.v1 as components
from deep_translator import GoogleTranslator
import edge_tts
import asyncio
import tempfile
import os
import re
import base64

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Global Translation | Real-Time. Real Dialogue. Seamless Global Conversations.",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# PROFESSIONAL UI/UX CSS & TYPOGRAPHY
# ==========================================
st.markdown(
    """
    <style>
        /* Increase global typography and remove default heavy margins */
        .block-container { padding-top: 2rem !important; }
        
        /* Make all paragraph text larger and more readable */
        .stMarkdown p { font-size: 1.1rem !important; color: #3c4043; }
        
        /* Style the input/output container cards */
        div[data-testid="stColumn"] {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #dadce0;
            box-shadow: 5px 1px 3px rgba(0, 0, 0, 0.05);
        }

        /* Enlarge Text Area Fonts for Readability */
        .stTextArea textarea {
            font-size: 1.25rem !important;
            line-height: 1.6 !important;
            border: 1px solid #dadce0 !important;
            border-radius: 8px !important;
            padding: 12px !important;
            background-color: #f8f9fa !important;
        }
        .stTextArea textarea:focus {
            border-color: #1a73e8 !important;
            background-color: #ffffff !important;
            box-shadow: inset 0 0 0 1px #1a73e8 !important;
        }

        /* Enlarge Dropdown Menus */
        .stSelectbox div[data-baseweb="select"] {
            font-size: 1.1rem !important;
        }
        .stSelectbox label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            color: #5f6368 !important;
        }

        /* Professional Primary Button */
        button[kind="primary"] {
            background-color: #1a73e8 !important;
            color: white !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            padding: 0.6rem 0 !important;
            border: none !important;
            width: 100% !important;
        }
        
        button[kind="primary"]:hover { 
            background-color: #1557b0 !important; 
        }

        button[kind="primary"]:focus {
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(26,115,232,0.3) !important;
        }

        /* Professional Secondary Buttons */
        button[kind="secondary"] p { font-size: 1.05rem !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# HELPERS
# ==========================================
def run_async(coro):
    try:
        asyncio.get_running_loop()
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    except RuntimeError:
        return asyncio.run(coro)

def get_languages():
    try:
        global_languages = GoogleTranslator().get_supported_languages(as_dict=True)
        return {k.title(): v for k, v in global_languages.items()}
    except Exception:
        return {
            "English": "en", "Hindi": "hi", "Spanish": "es", 
            "French": "fr", "German": "de"
        }

def translate_large_text_safely(text_data, src_code, tgt_code):
    text_data = text_data.strip()
    if not text_data: return ""

    raw_sentences = re.split(r'(?<=[.!?।])\s+', text_data)
    text_chunks, current_chunk = [], ""

    for sentence in raw_sentences:
        sentence = sentence.strip()
        if not sentence: continue
        if len(current_chunk) + len(sentence) + 1 <= 1500:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                text_chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    if current_chunk.strip():
        text_chunks.append(current_chunk.strip())

    translator = GoogleTranslator(source=src_code, target=tgt_code)
    final_translated_text = []

    for chunk in text_chunks:
        try:
            translated_part = translator.translate(chunk)
            final_translated_text.append(translated_part if translated_part else chunk)
        except Exception:
            final_translated_text.append(chunk)

    return " ".join(final_translated_text).strip()

def generate_voice_internal(text_data, target_lang_name):
    lang_lower = target_lang_name.lower()
    voice_profile = "en-IN-NeerjaNeural"
    if "hindi" in lang_lower: voice_profile = "hi-IN-SwaraNeural"
    elif "spanish" in lang_lower: voice_profile = "es-ES-ElviraNeural"
    elif "french" in lang_lower: voice_profile = "fr-FR-DeniseNeural"
    elif "german" in lang_lower: voice_profile = "de-DE-KatjaNeural"
    elif "italian" in lang_lower: voice_profile = "it-IT-ElsaNeural"
    elif "japanese" in lang_lower: voice_profile = "ja-JP-NanamiNeural"
    elif "chinese" in lang_lower: voice_profile = "zh-CN-XiaoxiaoNeural"
    elif "arabic" in lang_lower: voice_profile = "ar-EG-SalmaNeural"
    elif "russian" in lang_lower: voice_profile = "ru-RU-SvetlanaNeural"

    async def _save():
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            output_filepath = tmp_file.name
        communicate = edge_tts.Communicate(text_data, voice_profile)
        await communicate.save(output_filepath)
        return output_filepath

    return run_async(_save())

def get_history_index_by_title(title):
    for i, entry in enumerate(st.session_state.history):
        if entry["title"] == title: return i
    return None

def load_selected_history():
    selected_title = st.session_state.get("selected_history_title", "")
    idx = get_history_index_by_title(selected_title)
    if idx is None: return
    entry = st.session_state.history[idx]
    st.session_state.user_input_field = entry["input"]
    st.session_state.output_display_widget = entry["output"]
    st.session_state.src_select_ui = entry["src"]
    st.session_state.tgt_select_ui = entry["tgt"]
    st.session_state.rename_chat_input = entry["title"]

# ==========================================
# SESSION STATE
# ==========================================
if "history" not in st.session_state: st.session_state.history = []
if "translated_cache" not in st.session_state: st.session_state.translated_cache = ""
if "output_display_widget" not in st.session_state: st.session_state.output_display_widget = ""
if "play_source_audio" not in st.session_state: st.session_state.play_source_audio = False
if "play_output_audio" not in st.session_state: st.session_state.play_output_audio = False
if "rename_chat_input" not in st.session_state: st.session_state.rename_chat_input = ""
if "selected_history_title" not in st.session_state: st.session_state.selected_history_title = ""

languages = get_languages()
sorted_languages = sorted(languages.keys())

# ==========================================
# UI HEADER (With Pro SVG Logo)
# ==========================================
pro_icon_b64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzFBNzNFOCI+PHBhdGggZD0iTTEyLjg3IDE1LjA3bC0yLjU0LTIuNTEuMDMtLjAzYzEuNzQtMS45NCAyLjk4LTQuMTcgMy43MS02LjUzSDE3VjRoLTdWMkg4djJIMXYyaDExLjE3QzExLjUgNy45MiAxMC40NCA5Ljc1IDkgMTEuMzUgOC4wNyAxMC4zMiA3LjMgOS4xOSA2LjY5IDhoLTJjLjczIDEuNjMgMS43MyAzLjE3IDIuOTggNC41NmwtNS4wOSA1LjAyTDQgMTlsNS01IDMuMTEgMy4xMS43Ni0yLjA0ek0xOC41IDEwaC0yTDEyIDIyaDJsMS4xMi0zaDQuNzVMMjEgMjJoMmwtNC41LTEyem0tMi42MiA3bDEuNjItNC4zM0wxOS4xMiAxN2gtMy4yNHoiLz48L3N2Zz4="
icon_html = f"<img src='data:image/svg+xml;base64,{pro_icon_b64}' style='width: 46px; vertical-align: middle; margin-right: 12px; margin-bottom: 6px;'/>"

st.markdown(
    f"""
    <div style='margin-bottom: 2.5rem; text-align: center;'>
        <h1 style='font-size: 3.2rem; font-weight: 800; margin-bottom: 8px; color: #212529; letter-spacing: -1px;'>
            {icon_html}Global <span style='color: #1A73E8;'>Translation</span>
        </h1>
        <p style='font-size: 1.25rem; color: #6C757D; margin-top: 0; font-weight: 400;'>
            Real-Time. Real Dialogue. Seamless Global Conversations.
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

left_panel, right_panel = st.columns(2, gap="large")

# ==========================================
# LEFT PANEL (INPUT)
# ==========================================
with left_panel:
    st.markdown("#### :material/text_fields: Please Enter Your Text")

    source_lang = st.selectbox(
        "Select Input Language",
        ["Auto Detect"] + sorted_languages,
        key="src_select_ui"
    )

    input_text = st.text_area(
        "Enter text to process:",
        height=250,
        placeholder="Type or paste text here...",
        label_visibility="collapsed",
        key="user_input_field"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        trigger_translation = st.button("TRANSLATE NOW", type="primary", use_container_width=True)
    with col_b:
        play_source_clicked = st.button(":material/volume_up: Play Audio", use_container_width=True)

    if play_source_clicked:
        if input_text.strip():
            st.session_state.play_source_audio = True
        else:
            st.warning("Please enter text first.")

    if st.session_state.play_source_audio and input_text.strip():
        with st.spinner("Generating audio..."):
            try:
                audio_path = generate_voice_internal(input_text, source_lang)
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    with open(audio_path, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    os.unlink(audio_path)
            except Exception as e:
                st.warning(f"Audio failed: {e}")
            finally:
                st.session_state.play_source_audio = False

# ==========================================
# RIGHT PANEL (OUTPUT)
# ==========================================
with right_panel:
    st.markdown("#### :material/g_translate: Translation Result")

    target_lang = st.selectbox(
        "Select Destination Language",
        sorted_languages,
        index=sorted_languages.index("Hindi") if "Hindi" in sorted_languages else 0,
        key="tgt_select_ui"
    )

    if trigger_translation:
        if input_text.strip():
            with st.spinner("Translating..."):
                try:
                    src_code = "auto" if source_lang == "Auto Detect" else languages[source_lang]
                    tgt_code = languages[target_lang]
                    translation_result = translate_large_text_safely(input_text, src_code, tgt_code)

                    if translation_result.strip():
                        st.session_state.translated_cache = translation_result
                        st.session_state.output_display_widget = translation_result
                        st.session_state.history.append({
                            "title": f"Chat {len(st.session_state.history) + 1}",
                            "src": source_lang, "tgt": target_lang,
                            "input": input_text, "output": translation_result
                        })
                    else:
                        st.error("Empty result.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Provide input text first.")

    st.text_area(
        "Resulting translation output:",
        height=250,
        key="output_display_widget",
        label_visibility="collapsed"
    )

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button(":material/volume_up: Play Audio", key="play_out", use_container_width=True):
            if st.session_state.translated_cache.strip():
                st.session_state.play_output_audio = True
            else:
                st.warning("Translate text first.")

    with action_col2:
        st.download_button(
            label=":material/download: Download",
            data=st.session_state.translated_cache if st.session_state.translated_cache else "",
            file_name="translation.txt",
            mime="text/plain",
            use_container_width=True
        )

    # -------------------------------------------------------------
    # BULLETPROOF BASE64 HTML IFRAME (Prevents JS String Breaks)
    # -------------------------------------------------------------
    with action_col3:
        text_to_copy = st.session_state.translated_cache if st.session_state.translated_cache else input_text
        if text_to_copy.strip():
            # Safely encode the text into Base64 to prevent any quotes or newlines from breaking HTML/JS
            encoded_text = base64.b64encode(text_to_copy.encode('utf-8')).decode('utf-8')
            
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
                <style>
                    body {{ margin: 0; display: flex; align-items: center; justify-content: center; font-family: sans-serif; }}
                    .copy-btn {{
                        display: flex; align-items: center; justify-content: center; gap: 6px;
                        width: 100%; height: 40px; border-radius: 8px;
                        border: 1px solid #dadce0; background: #ffffff; color: #3c4043;
                        cursor: pointer; font-size: 1rem; transition: all 0.2s ease-in-out;
                    }}
                    .copy-btn:hover {{ border-color: #1a73e8; color: #1a73e8; background: #f8f9ff; }}
                    .material-symbols-outlined {{ font-size: 1.2rem; }}
                </style>
            </head>
            <body>
                <button class="copy-btn" id="copyBtn">
                    <span class="material-symbols-outlined" id="icon">content_copy</span>
                    <span id="text">Copy</span>
                </button>
                <script>
                    document.getElementById('copyBtn').addEventListener('click', function() {{
                        // Decode the base64 string back to normal text safely
                        const decodedText = decodeURIComponent(escape(window.atob('{encoded_text}')));
                        
                        navigator.clipboard.writeText(decodedText).then(() => {{
                            document.getElementById('icon').innerText = 'check';
                            document.getElementById('text').innerText = 'Copied';
                            setTimeout(() => {{
                                document.getElementById('icon').innerText = 'content_copy';
                                document.getElementById('text').innerText = 'Copy';
                            }}, 2000);
                        }}).catch(err => {{
                            console.error('Failed to copy: ', err);
                        }});
                    }});
                </script>
            </body>
            </html>
            """
            components.html(html_code, height=45)
        else:
            st.markdown(
                """
                <div style='display:flex;align-items:center;justify-content:center;gap:6px;width:100%;height:40px;border-radius:8px;border:1px solid #dadce0;background:#f8f9fa;color:#9aa0a6;opacity:0.7;cursor:not-allowed;font-family:sans-serif;'>
                    <span style='font-family: "Material Symbols Outlined"; font-size: 1.2rem;'></span> Copy
                </div>
                """,
                unsafe_allow_html=True
            )

    if st.session_state.play_output_audio and st.session_state.translated_cache.strip():
        with st.spinner("Generating audio..."):
            try:
                audio_path = generate_voice_internal(st.session_state.translated_cache, target_lang)
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    with open(audio_path, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    os.unlink(audio_path)
            except Exception as e:
                st.warning(f"Audio failed: {e}")
            finally:
                st.session_state.play_output_audio = False

# ==========================================
# SIDEBAR HISTORY
# ==========================================
st.sidebar.markdown("### :material/history: History")

if st.session_state.history:
    titles = [entry["title"] for entry in st.session_state.history]
    selected_title = st.sidebar.selectbox(
        "Saved chats", titles,
        index=titles.index(st.session_state.selected_history_title) if st.session_state.selected_history_title in titles else 0,
        key="selected_history_title", on_change=load_selected_history
    )

    st.sidebar.text_input("Rename chat", key="rename_chat_input")

    rename_col, delete_col = st.sidebar.columns(2)
    with rename_col:
        if st.button(":material/edit: Rename", use_container_width=True):
            idx = get_history_index_by_title(st.session_state.get("selected_history_title", ""))
            new_title = st.session_state.rename_chat_input.strip()
            if idx is not None and new_title:
                st.session_state.history[idx]["title"] = new_title
                st.session_state.selected_history_title = new_title
                st.rerun()

    with delete_col:
        if st.button(":material/delete: Delete", use_container_width=True):
            idx = get_history_index_by_title(st.session_state.get("selected_history_title", ""))
            if idx is not None:
                st.session_state.history.pop(idx)
                if st.session_state.history:
                    st.session_state.selected_history_title = st.session_state.history[max(0, min(idx, len(st.session_state.history) - 1))]["title"]
                    load_selected_history()
                else:
                    st.session_state.selected_history_title = ""
                    st.session_state.user_input_field = ""
                    st.session_state.output_display_widget = ""
                    st.session_state.translated_cache = ""
                    st.session_state.rename_chat_input = ""
                st.rerun()

    st.sidebar.markdown("---")
    if st.button(":material/delete_sweep: Clear Archive", use_container_width=True):
        st.session_state.history = []
        st.session_state.translated_cache = ""
        st.session_state.output_display_widget = ""
        st.session_state.user_input_field = ""
        st.session_state.rename_chat_input = ""
        st.session_state.selected_history_title = ""
        st.rerun()

    idx = get_history_index_by_title(st.session_state.get("selected_history_title", ""))
    if idx is not None:
        selected = st.session_state.history[idx]
        st.sidebar.info(f"**From:** {selected['src']} \n\n**To:** {selected['tgt']}")
else:
    st.sidebar.info("No saved chats yet. Translate text to record history.")