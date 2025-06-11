import requests
from io import BytesIO
from PyPDF2 import PdfReader
import streamlit as st

GITHUB_RAW_URL = "https://raw.githubusercontent.com/UnniAmbady/SecuritySystemQuiz/main/Security_Systems_Notes.pdf"

@st.cache_data
def fetch_pdf_in_chunks(url, chunk_size=1024):
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        return None

    content = BytesIO()
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            content.write(chunk)

    content.seek(0)
    return content

pdf_data = fetch_pdf_in_chunks(GITHUB_RAW_URL)

if pdf_data:
    reader = PdfReader(pdf_data)
    document = ""
    for page in reader.pages:
        document += page.extract_text() or ""
else:
    st.error("Failed to load Security_Systems_Notes.pdf from GitHub.")
    st.stop()
