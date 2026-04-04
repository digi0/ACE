import logging
import os

import pandas as pd

from backend.config import (
    VAULT_FILE, SHEET_NAME,
    HANDBOOK_FILE, HANDBOOK_SOURCE_NAME, HANDBOOK_SOURCE_LINK, BULLETIN_URL, BULLETIN_NAME,
    DS_HANDBOOK_FILE, DS_HANDBOOK_SOURCE_NAME, DS_HANDBOOK_SOURCE_LINK, DS_BULLETIN_URL, DS_BULLETIN_NAME,
)
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
    # ── CMPSC Excel vault ──────────────────────────────────────────────
    logger.info("Loading vault from %r (sheet=%r)", VAULT_FILE, SHEET_NAME)
    df = pd.read_excel(VAULT_FILE, sheet_name=SHEET_NAME)
    excel_records_raw = df.fillna("").to_dict(orient="records")
    excel_records = [normalize_excel_record(r, i) for i, r in enumerate(excel_records_raw)]
    logger.info("Loaded %d Excel vault records", len(excel_records))

    # ── CMPSC handbook ─────────────────────────────────────────────────
    logger.info("Loading CMPSC handbook from %r", HANDBOOK_FILE)
    handbook_records = load_handbook_chunks(
        HANDBOOK_FILE,
        source_name=HANDBOOK_SOURCE_NAME,
        source_link=HANDBOOK_SOURCE_LINK,
        title_prefix="CMPSC Handbook",
    )
    logger.info("Loaded %d CMPSC handbook chunks", len(handbook_records))

    # ── CMPSC bulletin ─────────────────────────────────────────────────
    bulletin_records = fetch_web_chunks(BULLETIN_URL, BULLETIN_NAME, source_type="web_bulletin")

    # ── DTSCE (Data Sciences) handbook ────────────────────────────────
    ds_handbook_records = []
    if os.path.exists(DS_HANDBOOK_FILE):
        logger.info("Loading DTSCE handbook from %r", DS_HANDBOOK_FILE)
        ds_handbook_records = load_handbook_chunks(
            DS_HANDBOOK_FILE,
            source_name=DS_HANDBOOK_SOURCE_NAME,
            source_link=DS_HANDBOOK_SOURCE_LINK,
            title_prefix="DTSCE Handbook",
        )
        logger.info("Loaded %d DTSCE handbook chunks", len(ds_handbook_records))
    else:
        logger.warning("DTSCE handbook not found at %r — skipping", DS_HANDBOOK_FILE)

    # ── DTSCE bulletin ────────────────────────────────────────────────
    ds_bulletin_records = fetch_web_chunks(DS_BULLETIN_URL, DS_BULLETIN_NAME, source_type="web_bulletin")

    # Priority: handbooks → bulletins → vault
    all_records = (
        handbook_records + ds_handbook_records
        + bulletin_records + ds_bulletin_records
        + excel_records
    )
    logger.info(
        "Total records: %d (cmpsc_handbook=%d, ds_handbook=%d, cmpsc_bulletin=%d, ds_bulletin=%d, vault=%d)",
        len(all_records), len(handbook_records), len(ds_handbook_records),
        len(bulletin_records), len(ds_bulletin_records), len(excel_records),
    )
    return all_records