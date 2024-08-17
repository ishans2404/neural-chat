import os
import shutil
import gradio as gr
from typing import List
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import requests
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_pdf_text(pdf_files):
    all_text = ""
    for pdf in pdf_files:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            all_text += page.extract_text()
    return all_text

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    elif parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        query_params = parse_qs(parsed_url.query)
        return query_params.get('v', [None])[0]
    return None

def extract_youtube_transcript(video_id):
    try:
        srt = YouTubeTranscriptApi.get_transcript(video_id)
        all_text = ""
        for dic in srt:
            all_text += dic['text'] + ' '
        return all_text
    except Exception as e:
        print(f"Error extracting YouTube transcript: {e}")
        return str(e)

def get_youtube_video_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url)
        data = response.json()
        return data['title']
    except Exception:
        return "Untitled YouTube Video"

def split_text_into_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=1200)
    text_chunks = splitter.split_text(text)
    return text_chunks

def create_vector_store(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def setup_conversation_chain(template):
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def process_files(files, youtube_url):
    all_text = ""
    uploaded_files = []

    # Process PDF files
    if files:
        os.makedirs("uploads", exist_ok=True)
        for file in files:
            # Extract just the filename from the full path
            filename = os.path.basename(file.name)
            file_path = os.path.join("uploads", filename)

            # Copy the file from the temporary location to our uploads directory
            shutil.copy(file.name, file_path)

            all_text += extract_pdf_text([file_path])
            uploaded_files.append({"name": filename, "type": "pdf"})

    # Process YouTube URL
    if youtube_url:
        video_id = extract_video_id(youtube_url)
        if video_id:
            transcript = extract_youtube_transcript(video_id)
            all_text += transcript
            video_title = get_youtube_video_title(video_id)
            uploaded_files.append({"name": video_title, "url": youtube_url})
        else:
            return "Invalid YouTube URL", ""

    if not all_text:
        return "No content to process", ""

    chunks = split_text_into_chunks(all_text)
    create_vector_store(chunks)

    # Remove uploaded files after processing
    if os.path.exists("uploads"):
        for file in os.listdir("uploads"):
            file_path = os.path.join("uploads", file)
            if os.path.exists(file_path):
                os.remove(file_path)

    # Format the file list for display
    file_list_text = "\n".join(
        [f"- **{file['name']}**" + (f" ([Link]({file['url']}))" if 'url' in file else "") for file in uploaded_files]
    )
    
    return "Content uploaded and processed successfully", file_list_text

def ask_question(question):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        indexed_data = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = indexed_data.similarity_search(question)

        prompt_template = """
        Your alias is NeuralChat. Your task is to provide a thorough response based on the given context, ensuring all relevant details are included.
        If the requested information isn't available, simply state, "answer not available in context," then answer based on your understanding, connecting with the context.
        Don't provide incorrect information.\n\n
        Context: \n {context}?\n
        Question: \n {question}\n
        Answer:
        """

        chain = setup_conversation_chain(prompt_template)
        response = chain({"input_documents": docs, "question": question}, return_only_outputs=True)

        return response["output_text"]
    except Exception as e:
        return f"An error occurred: {str(e)}"

def chat(message, history):
    response = ask_question(message)
    history.append((message, response))
    return history, ""

theme = gr.themes.Monochrome().set(
    button_primary_background_fill="#FF0000",
    button_primary_background_fill_hover="#FF0000",
)

# Gradio interface
def createApp():
    with gr.Blocks(theme=theme) as demo:
        gr.Markdown("# NeuralChat", elem_id="header")

        with gr.Row():
            with gr.Column(scale=2):
                files = gr.File(label="Upload PDF Files", file_count="multiple")
                youtube_url = gr.Textbox(label="YouTube URL")
                upload_button = gr.Button("Upload and Process")
                upload_output = gr.Textbox(label="Upload Status")
                file_list = gr.Markdown(label="Uploaded Files")

            with gr.Column(scale=5):
                chatbot = gr.Chatbot(show_copy_button=True, scale=1.5)
                msg = gr.Textbox(label="Ask a question", lines=1)
                upload_button.click(process_files, inputs=[files, youtube_url], outputs=[upload_output, file_list])
                msg.submit(chat, inputs=[msg, chatbot], outputs=[chatbot, msg])
    return demo

from fastapi import FastAPI

app = FastAPI()
gradioApp = createApp()

app = gr.mount_gradio_app(app, gradioApp, path="/")

@app.get("/")
def read_main():
    return {"message": "This is your main app. The Gradio demo is served at the root path."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
