import os

# ── Data files ────────────────────────────────────────────
VAULT_FILE    = "ACE_vlt.xlsx"
SHEET_NAME    = "PSU CMPSC"
HANDBOOK_FILE = "CMPSC-handbook-2024-2025.pdf"
INDEX_FILE    = "backend/data/ace_index.pkl"
UPLOAD_DIR    = "backend/uploads"

# ── PDF chunking ──────────────────────────────────────────
CHUNK_SIZE    = 500   # words per chunk
CHUNK_OVERLAP = 100   # words shared between consecutive chunks

# ── Handbook metadata ─────────────────────────────────────
HANDBOOK_SOURCE_NAME = "CMPSC-handbook-2024-2025.pdf"
HANDBOOK_SOURCE_LINK = "https://www.eecs.psu.edu/assets/docs/handbooks/CMPSC-handbook-2024-2025.pdf"

# ── Web sources ───────────────────────────────────────────
BULLETIN_URL  = "https://bulletins.psu.edu/undergraduate/colleges/engineering/computer-science-bs/"
BULLETIN_NAME = "CMPSC University Bulletin"

# ── OpenAI models ─────────────────────────────────────────
OPENAI_CHAT_MODEL      = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# ── Upload retention ──────────────────────────────────────
MAX_UPLOAD_FILES = 20   # keep only the N most-recently-modified files

# ── Logging ───────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
