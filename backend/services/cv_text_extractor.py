"""
CV Text Extractor - Extracts text from PDF and DOCX files.
"""
import os
import tempfile
from typing import Optional
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from uploaded CV file (PDF, DOC, DOCX).
    
    Args:
        file_content: Binary content of the file
        filename: Original filename with extension
        
    Returns:
        Extracted text content
    """
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name
    
    try:
        # Load based on file type
        if file_ext == '.pdf':
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()
            text = "\n\n".join([doc.page_content for doc in documents])
        elif file_ext in ['.doc', '.docx']:
            loader = UnstructuredWordDocumentLoader(tmp_path)
            documents = loader.load()
            text = "\n\n".join([doc.page_content for doc in documents])
        elif file_ext == '.txt':
            loader = TextLoader(tmp_path, encoding='utf-8')
            documents = loader.load()
            text = "\n\n".join([doc.page_content for doc in documents])
        else:
            # Fallback: try to decode as text
            text = file_content.decode('utf-8', errors='ignore')
        
        return text
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        # Fallback: try to decode as text
        try:
            return file_content.decode('utf-8', errors='ignore')
        except:
            return ""
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass
