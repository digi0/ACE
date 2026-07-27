import logging
import os

from backend.config import (
    HANDBOOK_FILE, HANDBOOK_SOURCE_NAME, HANDBOOK_SOURCE_LINK, BULLETIN_URL, BULLETIN_NAME,
    DS_HANDBOOK_FILE, DS_HANDBOOK_SOURCE_NAME, DS_HANDBOOK_SOURCE_LINK, DS_BULLETIN_URL, DS_BULLETIN_NAME,
)
from backend.data.pdf_ingestor import load_handbook_chunks
from backend.data.web_scraper import fetch_web_chunks

logger = logging.getLogger(__name__)


def load_psu_cmpsc_vault():
    """Build the CMPSC/DTSCE retrieval corpus: handbook chunks + bulletin chunks.

    This corpus only covers Computer Science and Data Sciences. Every other
    program is answered from the structured programs.json / courses.json data
    in program_service.py — see classify_major() in chat_service.py.
    """
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

    # Priority: handbooks → bulletins
    all_records = (
        handbook_records + ds_handbook_records
        + bulletin_records + ds_bulletin_records
    )
    logger.info(
        "Total records: %d (cmpsc_handbook=%d, ds_handbook=%d, cmpsc_bulletin=%d, ds_bulletin=%d)",
        len(all_records), len(handbook_records), len(ds_handbook_records),
        len(bulletin_records), len(ds_bulletin_records),
    )
    return all_records
