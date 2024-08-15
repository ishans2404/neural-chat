import os
import shutil
from typing import List, Union
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://neuralchat.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

# Configure Google API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class QuestionInput(BaseModel):
    question: str

class UploadInput(BaseModel):
    files: List[UploadFile] = File(...)
    youtube_url: str = Form(None)

def extract_pdf_text(pdfs):
    all_text = ""
    for pdf in pdfs:
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

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File([]), youtube_url: str = Form(None)):
    try:
        print(youtube_url)
        all_text = ""
        uploaded_files = []
        
        # Process PDF files
        if files:
            os.makedirs("uploads", exist_ok=True)
            for file in files:
                file_path = f"uploads/{file.filename}"
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                all_text += extract_pdf_text([file_path])
                uploaded_files.append({"name": file.filename, "type": "pdf"})
        
        # Process YouTube URL
        if youtube_url:
            video_id = extract_video_id(youtube_url)
            print(f"Extracted video ID: {video_id}")
            if video_id:
                transcript = extract_youtube_transcript(video_id)
                print(f"Extracted transcript: {transcript[:1000]}")  # Print the first 1000 characters for debugging
                all_text += transcript
                video_title = get_youtube_video_title(video_id)
                uploaded_files.append({"name": video_title, "type": "youtube", "url": youtube_url})
            else:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        if not all_text:
            raise HTTPException(status_code=400, detail="No content to process")

        chunks = split_text_into_chunks(all_text)
        create_vector_store(chunks)

        # Remove uploaded files after processing
        for file in os.listdir("uploads"):
            file_path = f"uploads/{file}"
            if os.path.exists(file_path):
                os.remove(file_path)

        return {"message": "Content uploaded and processed successfully", "uploaded_files": uploaded_files}
    except HTTPException as http_exc:
        print(f"HTTP Exception: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Unhandled Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/ask")
async def ask_question(question_input: QuestionInput):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        indexed_data = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = indexed_data.similarity_search(question_input.question)
        
        prompt_template = """
        Your alias is NeuralChat. Your task is to provide a thorough response based on the given context, ensuring all relevant details are included. 
        If the requested information isn't available, simply state, "answer not available in context," then answer based on your understanding, connecting with the context. 
        Don't provide incorrect information.\n\n
        Context: \n {context}?\n
        Question: \n {question}\n
        Answer:
        """
        
        chain = setup_conversation_chain(prompt_template)
        response = chain({"input_documents": docs, "question": question_input.question}, return_only_outputs=True)
        
        return {"answer": response["output_text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
