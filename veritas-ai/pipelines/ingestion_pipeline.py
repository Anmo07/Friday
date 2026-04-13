from typing import List
import asyncio
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from memory.vector_store import get_vector_store

async def ingest_documents_async(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200, batch_size: int = 50) -> int:
    """
    Phase 9: Asynchronous Batch Ingestion.
    Ingests raw Documents systematically via async boundaries. Spikes in large DOM mappings 
    are segmented out to prevent embedding pipeline tensor collisions and CPU blockages.
    """
    if not documents:
        return 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    if not chunks:
        return 0
        
    vector_store = get_vector_store()
    
    # Batch the execution cleanly
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        await asyncio.to_thread(vector_store.add_documents, documents=batch)
    
    return len(chunks)

def ingest_documents(documents: List[Document]) -> int:
    # Retain sync wrapping fallback
    return asyncio.run(ingest_documents_async(documents))
