import logging
import os
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from backend.config import INDEX_FILE, OPENAI_EMBEDDING_MODEL
from backend.data.vault_loader import load_psu_cmpsc_vault

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)


def get_embedding(text):
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def build_embedding_text(record):
    parts = [
        str(record.get("Title", "")).strip(),
        str(record.get("Category", "")).strip(),
        str(record.get("Subcategory", "")).strip(),
        str(record.get("Used_for", "")).strip(),
        str(record.get("Content", "")).strip(),
    ]

    return " | ".join(part for part in parts if part)


def build_index():
    logger.info("Building embedding index...")
    records = load_psu_cmpsc_vault()

    for i, record in enumerate(records):
        text_for_embedding = build_embedding_text(record)
        record["embedding"] = get_embedding(text_for_embedding)
        if (i + 1) % 50 == 0:
            logger.info("Embedded %d / %d records", i + 1, len(records))

    os.makedirs("backend/data", exist_ok=True)

    with open(INDEX_FILE, "wb") as f:
        pickle.dump(records, f)

    logger.info("Index built and saved to %r (%d records)", INDEX_FILE, len(records))
    return records


def load_index():
    if not os.path.exists(INDEX_FILE):
        logger.info("Index file not found — building from scratch")
        return build_index()

    logger.info("Loading index from %r", INDEX_FILE)
    with open(INDEX_FILE, "rb") as f:
        records = pickle.load(f)

    logger.info("Index loaded: %d records", len(records))
    return records


def delete_index_file():
    if os.path.exists(INDEX_FILE):
        os.remove(INDEX_FILE)
        return True
    return False