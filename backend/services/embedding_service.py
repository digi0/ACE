import re
import numpy as np
from backend.services.index_service import load_index, get_embedding

_cached_records = None


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        return 0.0

    return np.dot(a, b) / (a_norm * b_norm)


def extract_course_codes(text):
    pattern = r"\b([A-Za-z]{2,6}\s?\d{3})\b"
    matches = re.findall(pattern, text)
    cleaned = []

    for match in matches:
        code = re.sub(r"\s+", " ", match.upper()).strip()
        cleaned.append(code)

    return list(dict.fromkeys(cleaned))


def get_all_records_with_embeddings():
    global _cached_records

    if _cached_records is not None:
        return _cached_records

    _cached_records = load_index()
    return _cached_records


def keyword_score(question, record):
    q = question.lower()
    content = " ".join([
        str(record.get("Title", "")),
        str(record.get("Category", "")),
        str(record.get("Subcategory", "")),
        str(record.get("Used_for", "")),
        str(record.get("Content", "")),
    ]).lower()

    score = 0

    for word in q.split():
        if len(word) >= 4 and word in content:
            score += 0.05

    return score


def course_code_score(question, record):
    question_codes = extract_course_codes(question)

    if not question_codes:
        return 0.0

    record_text = " ".join([
        str(record.get("Title", "")),
        str(record.get("Content", "")),
        str(record.get("Subcategory", "")),
    ]).upper()

    score = 0.0

    for code in question_codes:
        if code in record_text:
            score += 0.35

    return score


def semantic_search(question, top_k=10):
    question_embedding = get_embedding(question)
    records = get_all_records_with_embeddings()

    scored_records = []

    for record in records:
        embedding = record.get("embedding")
        if embedding is None:
            continue

        semantic = cosine_similarity(question_embedding, embedding)
        keyword = keyword_score(question, record)
        course_boost = course_code_score(question, record)

        final_score = semantic + keyword + course_boost
        scored_records.append((final_score, record))

    scored_records.sort(key=lambda x: x[0], reverse=True)

    top_records = [record for score, record in scored_records[:top_k]]
    return top_records