import re


def normalize_text(text):
    return " ".join(str(text).split()).strip()


def split_into_rule_units(text):
    normalized = normalize_text(text)

    parts = re.split(r"[•\n;]+", normalized)
    cleaned_parts = []

    for part in parts:
        part = part.strip()
        if part:
            cleaned_parts.append(part)

    return cleaned_parts


def extract_course_codes(text):
    pattern = r"\b([A-Za-z]{2,6}\s?\d{3}[A-Za-z]?)\b"
    matches = re.findall(pattern, text)
    cleaned = []

    for match in matches:
        code = re.sub(r"\s+", " ", match.upper()).strip()
        cleaned.append(code)

    return list(dict.fromkeys(cleaned))


def extract_substitution_rules_from_text(text, source_title="", source_link=""):
    rules = []
    units = split_into_rule_units(text)

    for unit in units:
        normalized = normalize_text(unit)
        lowered = normalized.lower()

        if "substitute" not in lowered:
            continue

        course_codes = extract_course_codes(normalized)

        if len(course_codes) < 2:
            continue

        # Pattern 1:
        # "STAT/MATH 418 may substitute for 318 or 414"
        match = re.search(
            r"([A-Za-z]{2,6}\s?\d{3}[A-Za-z]?).*?may substitute for\s+(.+)",
            normalized,
            flags=re.IGNORECASE
        )

        if match:
            subject = re.sub(r"\s+", " ", match.group(1).upper()).strip()
            tail = match.group(2)
            tail_codes = extract_course_codes(tail)

            if not tail_codes:
                # handle abbreviated target numbers like "318 or 414"
                numbers = re.findall(r"\b(\d{3}[A-Za-z]?)\b", tail)
                prefix_match = re.match(r"([A-Za-z]{2,6})\s?\d{3}[A-Za-z]?", subject)
                prefix = prefix_match.group(1) if prefix_match else ""

                for number in numbers:
                    if prefix:
                        tail_codes.append(f"{prefix} {number}")

            for target in tail_codes:
                rules.append({
                    "rule_type": "substitution",
                    "subject": subject,
                    "relation": "can_substitute_for",
                    "object": target,
                    "source_text": normalized,
                    "source_title": source_title,
                    "source_link": source_link
                })
            continue

        # Pattern 2:
        # "combination of MATH 231 and MATH 232 may be substituted"
        combo_match = re.search(
            r"combination of\s+(.+?)\s+may be substituted",
            normalized,
            flags=re.IGNORECASE
        )

        if combo_match:
            combo_text = combo_match.group(1)
            combo_codes = extract_course_codes(combo_text)

            title_codes = extract_course_codes(source_title)

            if len(combo_codes) >= 2 and title_codes:
                subject = " + ".join(combo_codes[:2])
                target = title_codes[0]

                rules.append({
                    "rule_type": "replacement",
                    "subject": subject,
                    "relation": "can_replace",
                    "object": target,
                    "source_text": normalized,
                    "source_title": source_title,
                    "source_link": source_link
                })

    return rules


def extract_either_or_rules_from_text(text, source_title="", source_link=""):
    rules = []
    units = split_into_rule_units(text)

    for unit in units:
        normalized = normalize_text(unit)
        lowered = normalized.lower()

        if "either" not in lowered or "or" not in lowered:
            continue

        course_codes = extract_course_codes(normalized)

        if len(course_codes) < 2:
            continue

        rules.append({
            "rule_type": "either_or_requirement",
            "options": course_codes,
            "source_text": normalized,
            "source_title": source_title,
            "source_link": source_link
        })

    return rules


def extract_requirement_rules_from_text(text, source_title="", source_link=""):
    rules = []
    units = split_into_rule_units(text)

    for unit in units:
        normalized = normalize_text(unit)
        lowered = normalized.lower()

        trigger_phrases = ["required", "must complete", "need to complete"]

        if not any(phrase in lowered for phrase in trigger_phrases):
            continue

        course_codes = extract_course_codes(normalized)

        if not course_codes:
            continue

        # avoid giant noisy paragraphs
        if len(course_codes) > 8:
            continue

        rules.append({
            "rule_type": "requirement",
            "courses": course_codes,
            "source_text": normalized,
            "source_title": source_title,
            "source_link": source_link
        })

    return rules


def extract_rules_from_record(record):
    content = str(record.get("Content", "")).strip()
    title = str(record.get("Title", "")).strip()
    source_link = str(record.get("Source_link", "")).strip()

    if not content:
        return []

    rules = []
    rules.extend(extract_substitution_rules_from_text(content, title, source_link))
    rules.extend(extract_either_or_rules_from_text(content, title, source_link))
    rules.extend(extract_requirement_rules_from_text(content, title, source_link))

    return rules


def extract_rules_from_records(records):
    all_rules = []
    seen = set()

    for record in records:
        rules = extract_rules_from_record(record)

        for rule in rules:
            key = (
                rule.get("rule_type"),
                rule.get("subject"),
                rule.get("relation"),
                rule.get("object"),
                tuple(rule.get("options", [])) if "options" in rule else None,
                tuple(rule.get("courses", [])) if "courses" in rule else None,
                rule.get("source_text")
            )

            if key not in seen:
                seen.add(key)
                all_rules.append(rule)

    return all_rules