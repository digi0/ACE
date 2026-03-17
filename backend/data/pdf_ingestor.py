import logging

from pypdf import PdfReader

from backend.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    HANDBOOK_SOURCE_NAME,
    HANDBOOK_SOURCE_LINK,
)

logger = logging.getLogger(__name__)


def extract_pdf_pages(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            cleaned_text = text.strip()
            if cleaned_text:
                pages.append({
                    "page_number": page_number,
                    "text": cleaned_text
                })

    logger.info("extract_pdf_pages | %r → %d pages with text", pdf_path, len(pages))
    return pages


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks of `chunk_size` words,
    advancing `chunk_size - overlap` words between each chunk."""
    words = text.split()
    if not words:
        return []

    step = max(1, chunk_size - overlap)
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += step

    return chunks


def load_handbook_chunks(pdf_path):
    pages = extract_pdf_pages(pdf_path)
    records = []
    chunk_counter = 1

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]
        page_chunks = chunk_text(text)

        for chunk in page_chunks:
            records.append({
                "record_id": f"handbook_{chunk_counter}",
                "source_type": "pdf_handbook",
                "source_name": HANDBOOK_SOURCE_NAME,
                "page_number": page_number,
                "Title": f"CMPSC Handbook Page {page_number}",
                "Category": "handbook",
                "Subcategory": "",
                "Used_for": "",
                "Content": chunk.strip(),
                "Source_link": HANDBOOK_SOURCE_LINK
            })
            chunk_counter += 1

    logger.info("load_handbook_chunks | %d chunks from %r", len(records), pdf_path)
    return records