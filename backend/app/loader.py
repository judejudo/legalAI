import os
import asyncio
from uuid import uuid4
from tqdm import tqdm
from pdfminer.high_level import extract_text
from utils.splitter import TextSplitter
from openaiU import get_embeddings, token_size
from db import get_redis, setup_db, add_chunks_to_vector_db
from config import settings

def batchify(iterable, batch_size):
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i+batch_size]

async def process_docs(docs_dir=settings.DOCS_DIR):
    docs = []
    print('\nLoading documents')
    
    # Check if directory exists
    if not os.path.exists(docs_dir):
        print(f"Creating directory: {docs_dir}")
        os.makedirs(docs_dir)
    
    pdf_files = [f for f in os.listdir(docs_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in directory")
        return []
        
    for filename in tqdm(pdf_files):
        file_path = os.path.join(docs_dir, filename)
        try:
            text = extract_text(file_path)
            if not text.strip():  # Check if extracted text is empty
                print(f"\nWarning: No text extracted from {filename}")
                continue
            doc_name = os.path.splitext(filename)[0]
            docs.append((doc_name, text))
        except Exception as e:
            print(f"\nError processing {filename}: {str(e)}")
            continue
    
    print(f'\nSuccessfully loaded {len(docs)} out of {len(pdf_files)} PDF documents')
    
    if not docs:
        print("No documents were successfully processed")
        return []

    chunks = []
    text_splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
    print('\nSplitting documents into chunks')
    for doc_name, doc_text in docs:
        doc_id = str(uuid4())[:8]
        doc_chunks = text_splitter.split(doc_text)
        for chunk_idx, chunk_text in enumerate(doc_chunks):
            chunk = {
                'chunk_id': f'{doc_id}:{chunk_idx+1:04}',
                'text': chunk_text,
                'doc_name': doc_name,
                'vector': None
            }
            chunks.append(chunk)
        print(f'{doc_name}: {len(doc_chunks)} chunks')
    
    if not chunks:
        print("No chunks were created from the documents")
        return []
        
    chunk_sizes = [token_size(c['text']) for c in chunks]
    print(f'\nTotal chunks: {len(chunks)}')
    print(f'Min chunk size: {min(chunk_sizes)} tokens')
    print(f'Max chunk size: {max(chunk_sizes)} tokens')
    print(f'Average chunk size: {round(sum(chunk_sizes)/len(chunks))} tokens')

    vectors = []
    print('\nEmbedding chunks')
    with tqdm(total=len(chunks)) as pbar:
        for batch in batchify(chunks, batch_size=64):
            try:
                batch_vectors = await get_embeddings([chunk['text'] for chunk in batch])
                vectors.extend(batch_vectors)
                pbar.update(len(batch))
            except Exception as e:
                print(f"\nError processing batch: {str(e)}")
                continue

    for chunk, vector in zip(chunks, vectors):
        chunk['vector'] = vector
    return chunks

async def load_knowledge_base():
    async with get_redis() as rdb:
        print('Setting up Redis database')
        await setup_db(rdb)
        chunks = await process_docs()
        if chunks:
            print('\nAdding chunks to vector db')
            await add_chunks_to_vector_db(rdb, chunks)
            print('\nKnowledge base loaded')
        else:
            print('\nNo chunks to load into knowledge base')

def main():
    try:
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(load_knowledge_base())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        # Ensure proper cleanup
        if hasattr(asyncio, '_get_running_loop'):
            try:
                loop = asyncio._get_running_loop()
                if loop is not None and not loop.is_closed():
                    loop.close()
            except Exception:
                pass

if __name__ == '__main__':
    main()