import certifi
import os
os.environ['SSL_CERT_FILE'] = certifi.where()

import tiktoken
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
from config import settings

# Initialize the OpenAI client (for chat only)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
tokenizer = tiktoken.encoding_for_model(settings.MODEL)

# Initialize Sentence Transformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def token_size(text):
    return len(tokenizer.encode(text))

async def get_embedding(input):
    # Convert to numpy array and then to list for compatibility
    embedding = embedding_model.encode(input)
    return embedding.tolist()

async def get_embeddings(inputs):
    # Batch process embeddings
    embeddings = embedding_model.encode(inputs)
    return [emb.tolist() for emb in embeddings]

def chat_stream(messages, model=settings.MODEL, temperature=0.1, **kwargs):
    return client.beta.chat.completions.stream(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )