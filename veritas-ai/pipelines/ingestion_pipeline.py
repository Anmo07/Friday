from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from memory.vector_store import get_vector_store

def ingest_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> int:
    """
    Ingests a list of raw Documents. It will semantically split the text
    and store the result as embeddings inside the vector database.
    Returns: The number of successful chunks embedded and stored.
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
    # Add documents synchronously to chroma via direct API wrapper
    # In production, we'd batch this async for large drops
    vector_store.add_documents(documents=chunks)
    
    return len(chunks)
