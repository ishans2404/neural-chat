import os
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Function to extract text from PDFs
def extract_pdf_text(pdfs):
    all_text = ""
    for pdf in pdfs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            all_text += page.extract_text()
    return all_text
# Function to split text into chunks
def split_text_into_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=1200)
    text_chunks = splitter.split_text(text)
    return text_chunks
# Function to create vector store
def create_vector_store(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
# Function to setup conversation chain for QA
def setup_conversation_chain(template):
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain
# Function to handle user input based on selected mode
def handle_user_input(user_question=None):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    indexed_data = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = indexed_data.similarity_search(user_question)
    chain = setup_conversation_chain(prompt_template)
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    return response["output_text"]

prompt_template = """
Your alias is Neural-PDF. Your task is to provide a thorough response based on the given context, ensuring all relevant details are included. 
If the requested information isn't available, simply state, "answer not available in context," then answer based on your understanding, connecting with the context. 
Don't provide incorrect information.\n\n
Context: \n {context}?\n
Question: \n {question}\n
Answer:
"""