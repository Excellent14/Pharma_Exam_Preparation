import streamlit as st
import openai
import genai
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")
# Gemini API setup (or another alternative)
use_ai = os.getenv("USE_AI")  # "OpenAI" or "Gemini"
num_q = int(os.getenv("MCQ_COUNT", 5))  # Number of MCQs to generate

# Function to handle OCR text extraction
def extract_text(pdf_bytes, use_ocr=False):
    pdf_reader = PyPDF2.PdfReader(pdf_bytes)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text() or ""
    
    if use_ocr:
        images = convert_from_path(pdf_bytes)
        for img in images:
            text += pytesseract.image_to_string(img)
    return text

# Check if PDF is valid
def is_valid_pdf(pdf_bytes):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_bytes)
        return len(pdf_reader.pages) > 0
    except:
        return False

# Sanitizing the PDF file
def sanitize_pdf(file):
    # You can add custom sanitization rules here
    pass

# ---------- Main App ----------
st.title("AI Exam Agent")

f = st.file_uploader("Upload your PDF for notes and MCQs", type="pdf")
if f:
    sanitize_pdf(f)
    pdf_bytes = f.read()
    if not is_valid_pdf(pdf_bytes):
        st.error("Invalid PDF file")
        st.stop()

    # Extract text
    text = extract_text(pdf_bytes, use_ocr=True)
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
                        # If Ollama is not available, just skip this block
                        note = "⚠️ Error: Ollama is not available. Please use OpenAI or Gemini."
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
                    mcqs = "⚠️ Error: Ollama is not available. Please use OpenAI or Gemini."
            except Exception as e:
                mcqs = f"⚠️ Error: {str(e)}"
        st.subheader("Generated MCQs")
        st.markdown(mcqs)
else:
    st.info("Please upload a PDF to start generating notes or MCQs.")
