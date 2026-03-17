import logging

import pandas as pd

from backend.config import VAULT_FILE, SHEET_NAME, HANDBOOK_FILE, BULLETIN_URL, BULLETIN_NAME
from backend.data.pdf_ingestor import load_handbook_chunks
from backend.data.web_scraper import fetch_web_chunks

logger = logging.getLogger(__name__)


def normalize_excel_record(record, index):
    return {
        "record_id": f"excel_{index + 1}",
        "source_type": "excel_vault",
        "source_name": VAULT_FILE,
        "Title": str(record.get("Title", "")).strip(),
        "Category": str(record.get("Category", "")).strip(),
        "Subcategory": str(record.get("Subcategory", "")).strip(),
        "Used_for": str(record.get("Used_for", "")).strip(),
        "Content": str(record.get("Content", "")).strip(),
        "Source_link": str(record.get("Source_link", "")).strip(),
    }


def load_psu_cmpsc_vault():
    logger.info("Loading vault from %r (sheet=%r)", VAULT_FILE, SHEET_NAME)
    df = pd.read_excel(VAULT_FILE, sheet_name=SHEET_NAME)
    excel_records_raw = df.fillna("").to_dict(orient="records")

    excel_records = [
        normalize_excel_record(record, i)
        for i, record in enumerate(excel_records_raw)
    ]
    logger.info("Loaded %d Excel vault records", len(excel_records))

    logger.info("Loading handbook chunks from %r", HANDBOOK_FILE)
    handbook_records = load_handbook_chunks(HANDBOOK_FILE)
    logger.info("Loaded %d handbook chunks", len(handbook_records))

    bulletin_records = fetch_web_chunks(BULLETIN_URL, BULLETIN_NAME, source_type="web_bulletin")

    # Priority order: handbook (primary) → bulletin (secondary) → excel vault
    all_records = handbook_records + bulletin_records + excel_records
    logger.info("Total records: %d (handbook=%d, bulletin=%d, vault=%d)",
                len(all_records), len(handbook_records), len(bulletin_records), len(excel_records))
    return all_records