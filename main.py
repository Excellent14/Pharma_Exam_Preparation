import streamlit as st
import PyPDF2
import openai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import pdf2image
import requests
import json

# Load environment variables
load_dotenv()

# API keys and environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TIKTOKEN_API_KEY = os.getenv('TIKTOKEN_API_KEY')

# Setup OpenAI API
openai.api_key = OPENAI_API_KEY

# Streamlit app title and configuration
st.set_page_config(page_title="AI Exam Agent", page_icon=":books:", layout="wide")
st.title("AI Exam Agent for Pharma Exam Preparation")

# Function to process PDF and extract text
def process_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to generate MCQs using OpenAI API
def generate_mcqs(text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Create multiple choice questions from the following text:\n\n{text}",
        max_tokens=1000
    )
    return response.choices[0].text.strip()

# Function to extract text from an image using pytesseract
def extract_text_from_image(image):
    return pytesseract.image_to_string(image)

# File upload widget
pdf_file = st.file_uploader("Upload your PDF file", type=["pdf"])

# When the user uploads a file
if pdf_file:
    st.success("File uploaded successfully!")
    # Extract text from the PDF
    text = process_pdf(pdf_file)
    st.write("Extracted Text from PDF:")
    st.text_area("Text", text, height=300)

    # Generate MCQs
    if st.button("Generate MCQs"):
        mcqs = generate_mcqs(text)
        st.subheader("Generated MCQs:")
        st.write(mcqs)

    # Optional: Add support for images (to extract text from images in the PDF)
    image_file = st.file_uploader("Upload Image for Text Extraction", type=["png", "jpg", "jpeg"])

    if image_file:
        image = Image.open(image_file)
        extracted_text = extract_text_from_image(image)
        st.write("Extracted Text from Image:")
        st.text_area("Image Text", extracted_text, height=300)

# For custom features like API integration or other specific functions, add further logic
