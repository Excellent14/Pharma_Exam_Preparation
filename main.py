import streamlit as st
import PyPDF2
import pdfplumber
import os
from dotenv import load_dotenv
import openai
import genai
from PIL import Image
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to extract text from PDF using PyPDF2
def extract_pdf_text_pypdf2(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        return text
    except PyPDF2.errors.PdfReadError as e:
        return f"Error reading PDF with PyPDF2: {str(e)}"
    except Exception as e:
        return f"Unexpected error with PyPDF2: {str(e)}"

# Function to extract text from PDF using pdfplumber (fallback)
def extract_pdf_text_plumber(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        return f"Error reading PDF with pdfplumber: {str(e)}"

# Fallback function to handle PDF extraction
def extract_pdf_text(pdf_file):
    text = extract_pdf_text_pypdf2(pdf_file)
    if "Error" in text:  # If PyPDF2 failed, use pdfplumber
        text = extract_pdf_text_plumber(pdf_file)
    return text

# Function to generate MCQs based on extracted text
def generate_mcqs_from_text(text):
    prompt = f"Generate MCQs based on the following text:\n\n{text}\n\nMCQs:"
    
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=500
    )
    
    return response.choices[0].text.strip()

# Streamlit UI
st.title("AI Exam Agent for Pharma Exam Preparation")
st.sidebar.header("Upload PDF for MCQ Generation")

# File uploader for PDF
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    # Extract text from PDF
    pdf_text = extract_pdf_text(uploaded_file)

    if "Error" in pdf_text:
        st.error(f"Failed to extract text from PDF: {pdf_text}")
    else:
        st.success("PDF text extracted successfully!")

        # Show extracted text
        st.text_area("Extracted Text", pdf_text, height=300)

        # Generate MCQs
        if st.button("Generate MCQs"):
            mcqs = generate_mcqs_from_text(pdf_text)
            if mcqs:
                st.write(mcqs)
            else:
                st.error("No MCQs generated. Please check the extracted text.")

# Error handling for missing API keys in environment
if not openai.api_key:
    st.error("OpenAI API key is missing in the environment variables.")
