import streamlit as st
import os
import requests
from dotenv import load_dotenv
import PyPDF2

# Load .env variables
load_dotenv()
API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL = os.getenv("MODEL_NAME", "mistral-7b-instruct")

# Set headers for Together API
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Streamlit UI
st.set_page_config(page_title="AI Exam Agent", layout="centered")
st.title("📘 AI Exam Agent")
st.subheader("Generate Notes & MCQs from your PDF")

# File upload
pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# Extract text from PDF
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""
    return full_text

# Call Together API
def query_together(prompt):
    data = {
        "model": MODEL,
        "prompt": prompt,
        "max_tokens": 800,
        "temperature": 0.7,
    }
    response = requests.post("https://api.together.xyz/v1/completions", headers=HEADERS, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["text"].strip()
    else:
        return f"❌ Error: {response.status_code} - {response.text}"

# Notes & MCQs
if pdf_file:
    text = extract_text_from_pdf(pdf_file)
    st.success("✅ PDF text extracted successfully!")

    if st.button("📄 Generate Notes"):
        with st.spinner("Generating notes..."):
            notes_prompt = f"Generate detailed study notes from the following content:\n\n{text[:4000]}"
            notes = query_together(notes_prompt)
            st.subheader("📝 Generated Notes")
            st.write(notes)

    if st.button("❓ Generate MCQs"):
        with st.spinner("Generating MCQs..."):
            mcq_prompt = f"Generate 5 multiple choice questions with options and answers from the following text:\n\n{text[:4000]}"
            mcqs = query_together(mcq_prompt)
            st.subheader("📊 Generated MCQs")
            st.write(mcqs)
