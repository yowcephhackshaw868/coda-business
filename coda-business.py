import streamlit as st
import google.generativeai as genai
import json
from PIL import Image

# --- 0. API SETUP ---
# Grabbing your key securely from Streamlit's secret vault
# This looks for the key, but won't crash the app if it can't find it!
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)

if GEMINI_API_KEY is None:
    st.error("⚠️ I couldn't find your GEMINI_API_KEY in the Streamlit Secrets!")
    st.info("Please add it to your app settings on the Streamlit Cloud dashboard.")
    st.stop() # This stops the app gracefully instead of showing a red crash screen

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 1. SETTING THE MOOD ---
st.set_page_config(page_title="Corporate Strategy Hub", layout="centered")

st.markdown("""
    <style>
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. THE INTERFACE & FILE UPLOADER ---
st.title("Corporate Strategy Hub")
st.write("Upload business documents, data, or screenshots to analyze alongside your prompt.")

with st.sidebar:
    st.header("🏢 Strategy Settings")
    user_persona = st.selectbox("Advisory Style", ["Direct Executive", "Data-Driven Analyst", "Creative Problem Solver"])
    user_domain = st.selectbox("Focus Area", ["Operations & Scale", "Financial & P&L", "Product & Tech", "HR & Culture"])
    
    st.divider()
    
    # NEW: File uploader for Screenshots, PDFs, and data!
    uploaded_file = st.file_uploader(
        "Attach corporate files or screenshots", 
        type=["png", "jpg", "jpeg", "pdf", "csv", "txt"]
    )
    
    if uploaded_file is not None:
        st.success(f"📎 Loaded: {uploaded_file.name}")
        
    st.divider()
    if st.button("Clear Thread"):
        st.session_state.messages = []
        st.rerun()

# --- 3. DISPLAY CONVERSATION HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. HANDLE NEW INPUT & MULTIMODAL ANALYSIS ---
if prompt := st.chat_input("Ask a question or request an analysis..."):
    
    # 1. Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Package the payload (Text + Files if available)
    contents_payload = []
    
    # If a file was uploaded, process it based on type
    if uploaded_file is not None:
        file_type = uploaded_file.type
        
        # Handle Screenshots/Images
        if "image" in file_type:
            img = Image.open(uploaded_file)
            contents_payload.append(img)
            
        # Handle raw text files or CSVs
        elif "text" in file_type or "csv" in file_type:
            text_data = uploaded_file.read().decode("utf-8")
            contents_payload.append(f"--- ATTACHED FILE DATA ---\n{text_data}\n------------------------")
            
        # Handle PDFs (Gemini can process raw PDF bytes directly!)
        elif "pdf" in file_type:
            contents_payload.append({
                "mime_type": "application/pdf",
                "data": uploaded_file.read()
            })

    # 3. Build the smart prompt frame
    system_frame = f"""
    You are a corporate advisor handling high-level business issues.
    Style: {user_persona}.
    Core focus: {user_domain}.

    You are speaking with an executive. Keep answers highly professional, structured, and strategic. 
    If a file or image is provided below, analyze it deeply to answer the prompt. Look for trends, risks, or key data points.
    
    User prompt: "{prompt}"
    """
    
    # Add the prompt frame to our actual asset payload
    contents_payload.append(system_frame)
    
    # 4. Generate the response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Send the entire list of mixed media directly to Gemini!
            response = model.generate_content(contents_payload, stream=True)
            
            full_response = ""
            for chunk in response:
                full_response += chunk.text
                message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Could not connect to AI: {str(e)}")
