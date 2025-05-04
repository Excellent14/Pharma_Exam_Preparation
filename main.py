import streamlit as st
import openai
import google.generativeai as genai
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes
import pytesseract
import subprocess
import os
import pickle
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256

# ---------- Rate Limiter ----------
class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def allow(self):
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.period]
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False

limiter = RateLimiter(max_calls=100, period=60)

# ---------- API Keys ----------
OPENAI_API_KEY = os.getenv('OPENAI_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_KEY')

# ---------- Streamlit Setup ----------
st.set_page_config(page_title="AI Exam Agent", layout="wide")
st.title("📘 AI Exam Preparation Agent")

# ---------- Sidebar Controls ----------
sb = st.sidebar
num_q = sb.slider("Number of MCQs", 1, 100, 10)
note_depth = sb.selectbox("Note Depth", ["Concise", "Detailed", "Comprehensive"])
topic = sb.text_input("Topic (optional, use for focused MCQs)")
use_ocr = sb.checkbox("Enable OCR for scanned PDFs")
use_ai = sb.radio("AI Backend", ["Mistral", "OpenAI", "Gemini"])

# ---------- User Identification & GDPR ----------
user_name = st.text_input("Enter your name")
if not user_name.strip():
    st.warning("Please enter your name to proceed.")
    st.stop()
if st.checkbox("Delete my data"):
    try:
        os.remove("user_data.json")
        st.success("Data deleted as per GDPR")
    except FileNotFoundError:
        pass

# ---------- Dyslexia Mode ----------
if st.sidebar.checkbox("Dyslexia Mode"):
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=OpenDyslexic&display=swap');
    * { font-family: 'OpenDyslexic', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ---------- In-Memory Cache ----------
REDIS_STORE = {}
def get_cache_key(pdf_bytes): return sha256(pdf_bytes).hexdigest()
def check_redis(key): return REDIS_STORE.get(key)
def store_redis(key, val): REDIS_STORE[key] = val

# ---------- Model Prewarm ----------
def prewarm_ai():
    if use_ai == "OpenAI":
        if not OPENAI_API_KEY:
            st.error("OPENAI_KEY not set in environment")
            st.stop()
        openai.api_key = OPENAI_API_KEY
        threading.Thread(target=lambda: openai.chat.completions.create(model="gpt-4", messages=[{"role":"user","content":"warmup"}])).start()
    elif use_ai == "Gemini":
        if not GEMINI_API_KEY:
            st.error("GEMINI_KEY not set in environment")
            st.stop()
        genai.configure(api_key=GEMINI_API_KEY)

prewarm_ai()

# ---------- PDF Extraction ----------
@st.cache_data
def extract_text(pdf_bytes, ocr_enabled):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    if not text.strip() and ocr_enabled:
        key = get_cache_key(pdf_bytes)
        cached = check_redis(key)
        if not cached:
            images = convert_from_bytes(pdf_bytes)
            with ProcessPoolExecutor() as executor:
                ocr_chunks = list(executor.map(lambda img: pytesseract.image_to_string(img.convert('L')), images))
            cached = pickle.dumps("\n".join(ocr_chunks))
            store_redis(key, cached)
        text = pickle.loads(cached)
    return text

# ---------- PDF Validation ----------
def sanitize_pdf(uploaded_file):
    if len(uploaded_file.getvalue()) > 50 * 1024 * 1024:
        st.error("File too large (>50MB)")
        st.stop()

def is_valid_pdf(pdf_bytes):
    try:
        fitz.open(stream=pdf_bytes, filetype="pdf")
        return True
    except:
        return False

# ---------- Main App ----------
f = st.file_uploader("Upload your PDF for notes and MCQs", type="pdf")
if f:
    sanitize_pdf(f)
    pdf_bytes = f.read()
    if not is_valid_pdf(pdf_bytes):
        st.error("Invalid PDF file")
        st.stop()

    # Extract text
    text = extract_text(pdf_bytes, use_ocr)
    if not text.strip():
        st.error("No text extracted from PDF.")
        st.stop()
    st.success("PDF text extracted.")

    # Show Generate buttons
    if st.button("📝 Generate Notes"):
        notes = []
        with st.spinner("Generating notes..."):
            for idx, chunk in enumerate([text[i:i+3000] for i in range(0, len(text), 3000)]):
                prompt = f"Generate {note_depth.lower()} notes for exam from this content:\n{chunk}"
                try:
                    if use_ai == "OpenAI":
                        resp = openai.chat.completions.create(model="gpt-4", messages=[{"role": "user", "content": prompt}])
                        note = resp.choices[0].message.content
                    elif use_ai == "Gemini":
                        chat = genai.GenerativeModel('gemini-pro').start_chat()
                        response = chat.send_message(prompt)
                        note = response.text
                    else:
                        result = subprocess.run(
                            ["ollama", "run", "mistral"],
                            input=prompt.encode('utf-8'),
                            capture_output=True,
                            timeout=60
                        )
                        note = result.stdout.decode('utf-8').strip()
                        if not note:
                            note = "⚠️ Mistral did not return a valid response. Check Ollama setup."
                except Exception as e:
                    note = f"⚠️ Error: {str(e)}"
                notes.append(note)
        st.subheader("Generated Notes")
        st.markdown("\n\n".join(notes))

    if st.button("❓ Generate MCQs"):
        with st.spinner("Generating MCQs..."):
            try:
                if use_ai == "OpenAI":
                    mcq_resp = openai.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": f"Generate {num_q} MCQs from this text:\n{text}"}]
                    )
                    mcqs = mcq_resp.choices[0].message.content
                elif use_ai == "Gemini":
                    chat = genai.GenerativeModel('gemini-pro').start_chat()
                    response = chat.send_message(f"Generate {num_q} MCQs from this text:\n{text}")
                    mcqs = response.text
                else:
                    result = subprocess.run(
                        ["ollama", "run", "mistral"],
                        input=f"Generate {num_q} MCQs from this text:\n{text}".encode('utf-8'),
                        capture_output=True,
                        timeout=60
                    )
                    mcqs = result.stdout.decode('utf-8').strip()
                    if not mcqs:
                        mcqs = "⚠️ Mistral did not return MCQs."
            except Exception as e:
                mcqs = f"⚠️ Error: {str(e)}"
        st.subheader("Generated MCQs")
        st.markdown(mcqs)
else:
    st.info("Please upload a PDF to start generating notes or MCQs.")
