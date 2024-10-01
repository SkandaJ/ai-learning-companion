import PyPDF2
import google.generativeai as gen_ai
import os

from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
gen_ai.configure(api_key=GOOGLE_API_KEY)

def summarize_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    summary = gen_ai.summarize(text)
    return summary

def ask_question(pdf_text, question):
    response = gen_ai.ask(question=question, context=pdf_text)
    return response
