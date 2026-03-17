from backend.data.vault_loader import load_psu_cmpsc_vault

vault_records = load_psu_cmpsc_vault()


def get_all_vault_records():
    return vault_records


def search_vault(category=None, used_for=None, keyword=None):
    results = vault_records

    if category:
        results = [
            record for record in results
            if record["Category"].lower() == category.lower()
        ]

    if used_for:
        results = [
            record for record in results
            if record["Used_for"].lower() == used_for.lower()
        ]

    if keyword:
        keyword = keyword.lower()
        results = [
            record for record in results
            if keyword in record["Title"].lower() \
            or keyword in record["Subcategory"].lower() \
            or keyword in record["Category"].lower() \
            or keyword in record.get("Content", "").lower()
        ]

    return results


def build_vault_context(records):
    context_parts = []

    for r in records:
        if "Content" in r and r["Content"]:
            context_parts.append(r["Content"])
        else:
            title = r.get("Title", "")
            category = r.get("Category", "")
            context_parts.append(f"{title} ({category})")

    return "\n\n".join(context_parts[:8])