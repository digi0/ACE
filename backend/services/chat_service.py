import logging
import os
import re
import json
from datetime import date, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from backend.config import OPENAI_CHAT_MODEL
from backend.services.embedding_service import semantic_search
from backend.services.cost_service import record_usage
from backend.services.student_doc_service import (
    has_student_doc,
    build_student_doc_context,
    get_current_student_doc,
    get_user_major,
)
from backend.services.program_service import (
    get_program,
    build_program_context_snippet,
    get_double_dips,
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)


def detect_question_intent(question):
    q = question.lower()

    course_keywords = [
        "course", "courses", "class", "classes",
        "math", "stat", "cmpsc", "ds ", " ds ", "dtsce",
        "data sciences", "data science", "credits",
        "requirement", "requirements", "take", "need"
    ]

    contact_keywords = [
        "advisor", "adviser", "contact", "email", "phone",
        "office", "who do i talk to", "who should i contact"
    ]

    transfer_keywords = [
        "transfer", "transferring", "credit transfer", "transfer credit",
        "credits from another school", "advanced placement",
        "international baccalaureate", "ap credit", "ib credit",
        "ap exam", "ap score", "ap scores",
    ]
    # "ap"/"ib" alone need word boundaries — bare substrings match
    # "apply"/"flexible". Match only the standalone acronyms.
    transfer_acronym = re.search(r"\b(ap|ib)\b", q)

    etm_keywords = [
        "etm", "entrance to major", "major entry"
    ]

    substitution_keywords = [
        "substitute", "substitution", "replace", "instead of", "count for"
    ]

    personal_progress_keywords = [
    "i still need",
    "do i still need",
    "can i graduate",
    "graduation",
    "my degree audit",
    "my transcript",
    "my what-if",
    "what courses do i still need",
    "what do i have left",
    "remaining courses",
    "remaining requirements",
    "if i fail",
    "if i get an f",
    "my standing",
    "my gpa",
    "how many courses do i still need",
    "how many credits do i still need",
    "how many courses do i still need to take",
    "how many classes do i still need",
    "what courses do i need to graduate",
    "what do i still need to graduate",
    # additional phrasings
    "what courses do i still have",
    "still have to complete",
    "still have to take",
    "still have to finish",
    "courses left",
    "credits left",
    "what's left",
    "what is left",
    "how much is left",
    "what do i have to complete",
    "what do i have to take",
    "what do i have to finish",
    "what else do i need",
    "what else do i have",
    "what requirements are left",
    "requirements left",
    "how far along",
    "am i on track",
    "my progress",
    "degree progress",
    "how close am i",
    ]


    gen_ed_keywords = [
        "gen ed", "general education", "gened", "ga ", " ga ", "gh ", " gh ",
        "gq ", " gq ", "gn ", " gn ", "gs ", " gs ", "gha", "us culture",
        "international culture", " il ", "il course", "arts requirement",
        "humanities requirement", "social science requirement",
        "natural science requirement", "quantification", "health requirement",
        "diversity requirement", "writing requirement", "speaking requirement",
        "gen ed requirement", "gen-ed", "general ed",
        "what counts for", "what satisfies", "double dip", "double-dip",
        "kines 082", "phil 010", "musc 007", "musc 008", "thea 100",
        "psych 100", "econ 102", "anth 001", "intl 100",
    ]

    deadline_keywords = [
        "deadline", "deadlines", "due date", "last day to", "last day of",
        "drop/add", "drop add", "add/drop", "add drop",
        "withdraw", "withdrawal", "late drop", "late withdrawal",
        "registration", "register", "enroll", "enrollment",
        "when can i register", "when does registration",
        "academic calendar", "calendar", "schedule of classes",
        "final exam", "finals week", "finals schedule",
        "semester end", "semester ends", "last day of class",
        "spring 2026", "fall 2026", "summer 2026",
        "tuition due", "payment deadline", "bill due",
        "grade appeal", "grade deadline",
    ]

    wellbeing_keywords = [
        "stress", "stressed", "anxiety", "anxious", "overwhelmed", "burnout",
        "mental health", "depressed", "depression", "struggling", "counseling",
        "caps", "uhs", "health", "sick", "therapy", "therapist", "crisis",
        "emergency fund", "financial hardship", "broke", "can't afford",
        "safe walk", "unsafe", "harassed", "emergency", "campus police",
        "extracurricular", "club", "clubs", "org", "student org", "orgcentral",
        "rec", "recreation", "gym", "intramural", "career", "internship",
        "resume", "job", "handshake", "writing center", "tutoring", "lrc",
        "calc", "calculus help",
    ]

    # Visa/immigration — unambiguous, checked first; ACE refers, never advises.
    # Visa/immigration acronyms need WORD BOUNDARIES — bare substrings like "opt"
    # or "ead" false-match "option"/"deadline". Regex for the short tokens,
    # plain phrases for the longer ones.
    intl_acronym = re.search(
        r"\b(opt|cpt|ead|dso|sevis|uscis|dissa|visas?|i-?20|i-?94|ds-?2019|f-?1|j-?1|h-?1b)\b",
        q,
    )
    international_phrases = [
        "international student", "optional practical training",
        "curricular practical training", "immigration", "travel signature",
        "out of status", "study permit", "work authorization",
        "penn state global", "designated school official",
    ]

    financial_aid_keywords = [
        "financial aid", "fafsa", "scholarship", "scholarships", "grant", "grants",
        "student loan", "student loans", "work study", "work-study", "student aid",
        "net price", "cost of attendance", "pay for college", "pay for school",
        "paying for college", "afford tuition", "aid package", "aid eligibility",
        "pell grant", "subsidized loan", "loan forgiveness", "tuition assistance",
    ]

    if intl_acronym or any(p in q for p in international_phrases):
        return "international"

    if any(keyword in q for keyword in financial_aid_keywords):
        return "financial_aid"

    if any(keyword in q for keyword in deadline_keywords):
        return "deadline"

    if any(keyword in q for keyword in gen_ed_keywords):
        return "gen_ed"

    if any(keyword in q for keyword in wellbeing_keywords):
        return "wellbeing"

    if any(keyword in q for keyword in personal_progress_keywords):
        return "student_progress"

    if any(keyword in q for keyword in contact_keywords):
        return "contact"

    if transfer_acronym or any(keyword in q for keyword in transfer_keywords):
        return "transfer"

    if any(keyword in q for keyword in etm_keywords):
        return "etm"

    if any(keyword in q for keyword in substitution_keywords):
        return "substitution"

    if any(keyword in q for keyword in course_keywords):
        return "courses"

    return "general"


def select_top_records(records, intent):
    handbook = [r for r in records if r.get("source_type") == "pdf_handbook"]
    bulletin = [r for r in records if r.get("source_type") == "web_bulletin"]

    if intent in ["courses", "student_progress"]:
        # Handbook is primary, bulletin secondary
        return handbook[:4] + bulletin[:3]

    if intent == "substitution":
        return handbook[:4] + bulletin[:2]

    if intent in ["transfer", "etm", "contact"]:
        # Procedural questions — the handbooks carry ETM rules, petitions,
        # substitution process, and department contacts; the bulletins don't.
        return handbook[:4] + bulletin[:2]

    if intent == "gen_ed":
        return handbook[:3] + bulletin[:3]

    if intent == "deadline":
        return bulletin[:2] + handbook[:2]

    # general
    return bulletin[:2] + handbook[:3]


def format_record_for_context(record, index):
    lines = [
        f"Record {index}:",
        f"Title: {record.get('Title', '')}",
        f"Category: {record.get('Category', '')}",
    ]

    subcategory = record.get("Subcategory", "")
    used_for = record.get("Used_for", "")
    source_type = record.get("source_type", "")
    source_name = record.get("source_name", "")
    page_number = record.get("page_number", "")
    content = record.get("Content", "")
    source_link = record.get("Source_link", "")

    if subcategory:
        lines.append(f"Subcategory: {subcategory}")

    if used_for:
        lines.append(f"Used for: {used_for}")

    if source_type:
        lines.append(f"Source type: {source_type}")

    if source_name:
        lines.append(f"Source name: {source_name}")

    if page_number:
        lines.append(f"Page number: {page_number}")

    lines.append(f"Content: {content}")

    if source_link:
        lines.append(f"Source link: {source_link}")

    return "\n".join(lines)


def build_context_from_records(records):
    if not records:
        return "No relevant advising records were found."

    context_parts = []

    for index, record in enumerate(records, start=1):
        context_parts.append(format_record_for_context(record, index))

    return "\n\n---\n\n".join(context_parts)


def build_sources(records):
    handbook_source = None
    bulletin_source = None

    for record in records:
        source_link = str(record.get("Source_link", "")).strip()
        source_type = str(record.get("source_type", "")).strip().lower()

        if not source_link:
            continue

        if source_type == "pdf_handbook" and handbook_source is None:
            source_name = str(record.get("source_name", "")).lower()
            label = "DTSCE Handbook" if "dtsce" in source_name else "CMPSC Handbook"
            handbook_source = {"title": label, "link": source_link}

        elif source_type == "web_bulletin" and bulletin_source is None:
            source_name = str(record.get("source_name", "")).lower()
            label = "DTSCE University Bulletin" if "dtsce" in source_name else "CMPSC University Bulletin"
            bulletin_source = {"title": label, "link": source_link}

    sources = []

    if handbook_source is not None:
        sources.append(handbook_source)

    if bulletin_source is not None:
        sources.append(bulletin_source)

    return sources


def classify_major(major_name):
    """Classify the student's selected major by how ACE can ground answers for it.

    Only CMPSC and DTSCE have content in the RAG index (the two handbooks and
    their bulletins). Every other major is answered from the structured
    programs.json data instead, so the CS/DS handbook records don't leak into
    and skew answers for unrelated majors.

    Returns:
        'cs'    — a Computer Science program (any campus) → RAG handbook applies
        'ds'    — a Data Sciences program (any campus)    → RAG handbook applies
        'other' — any other program → answer from programs.json only
        None    — no major selected → keep the default (question-driven) behavior
    """
    if not major_name:
        return None
    nl = major_name.lower()
    # NB: this must match "Computer Science, B.S. (Engineering)" — the UP program
    # the CMPSC handbook and BULLETIN_URL actually document. An earlier
    # `and "engineering" not in nl` guard excluded exactly that one program.
    if "computer science" in nl:
        return "cs"
    if "data scien" in nl or "computational data" in nl:
        return "ds"
    return "other"


def build_program_sources(major_name):
    """Build the source link for a structured-only major from programs.json."""
    prog = get_program(major_name) if major_name else None
    if not prog:
        return []
    url = str(prog.get("url") or "").strip()
    if not url:
        return []
    return [{"title": f"{prog['program_name']} — Penn State Bulletin", "link": url}]


def extract_course_codes(text):
    pattern = r"\b([A-Za-z]{2,6}\s?\d{3})\b"
    matches = re.findall(pattern, text)
    cleaned = []

    for match in matches:
        code = re.sub(r"\s+", " ", match.upper()).strip()
        cleaned.append(code)

    return list(dict.fromkeys(cleaned))


def extract_requirement_rules(records):
    rules = {
        "course_codes": [],
        "substitution_lines": [],
        "either_or_lines": [],
        "required_lines": []
    }

    seen_codes = set()
    seen_lines = set()

    for record in records:
        content = str(record.get("Content", "")).strip()
        if not content:
            continue

        for code in extract_course_codes(content):
            if code not in seen_codes:
                seen_codes.add(code)
                rules["course_codes"].append(code)

        lowered = content.lower()
        normalized = " ".join(content.split())

        if "substitute" in lowered and normalized not in seen_lines:
            seen_lines.add(normalized)
            rules["substitution_lines"].append(normalized)

        if "either" in lowered and "or" in lowered and normalized not in seen_lines:
            seen_lines.add(normalized)
            rules["either_or_lines"].append(normalized)

        if (
            ("required" in lowered or "must complete" in lowered or "need to complete" in lowered)
            and normalized not in seen_lines
        ):
            seen_lines.add(normalized)
            rules["required_lines"].append(normalized)

    return rules


def build_rule_summary(rules):
    parts = []

    if rules["course_codes"]:
        parts.append("Detected course codes: " + ", ".join(rules["course_codes"][:20]))

    if rules["substitution_lines"]:
        parts.append("Substitution rules:")
        for line in rules["substitution_lines"][:5]:
            parts.append(f"- {line}")

    if rules["either_or_lines"]:
        parts.append("Either/or rules:")
        for line in rules["either_or_lines"][:5]:
            parts.append(f"- {line}")

    if rules["required_lines"]:
        parts.append("Requirement rules:")
        for line in rules["required_lines"][:5]:
            parts.append(f"- {line}")

    return "\n".join(parts) if parts else "No explicit rule lines were extracted."


def build_student_progress_answer(student_doc):
    audit = student_doc.get("audit_parse") or {}
    if not audit:
        return None

    unsatisfied_blocks = audit.get("unsatisfied_blocks", [])
    remaining_required = audit.get("remaining_required_courses", [])
    in_progress = audit.get("in_progress_courses", [])
    overall_totals = audit.get("overall_totals", {})
    advisor = audit.get("advisor")

    lines = []

    # ── Overall credit summary at the top ──────────────────────────────
    if overall_totals:
        best_key = max(overall_totals, key=lambda k: overall_totals[k].get("required", 0))
        t = overall_totals[best_key]
        req  = t.get("required", 0)
        used = t.get("used", 0)
        needed = t.get("needed", 0)
        pct = round(used / req * 100, 1) if req > 0 else 0
        lines.append(
            f"Based on your uploaded what-if report, you have completed **{used:.0f} of {req:.0f} credits** "
            f"({pct}% complete), with **{needed:.0f} credits still needed** to graduate."
        )
    else:
        lines.append("Based on your uploaded what-if report, here is what still appears to be pending for graduation:")

    # ── Compulsory/prescribed courses ──────────────────────────────────
    if remaining_required:
        lines.append("")
        lines.append("### Required courses still pending (C or higher required)")
        for course in remaining_required:
            lines.append(f"- **{course}**")

    # ── Other unsatisfied blocks ────────────────────────────────────────
    seen_titles = set()
    non_prescribed = []
    or_group_blocks = []

    for block in unsatisfied_blocks:
        title = (block.get("title") or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        if "PRESCRIBED" in title.upper():
            continue  # already shown above

        if re.match(r'^\*?OR\*?\s*Group\s+\d+|^Group\s+\d+$', title, re.IGNORECASE):
            or_group_blocks.append(block)
            continue

        non_prescribed.append(block)

    if non_prescribed or or_group_blocks:
        lines.append("")
        lines.append("### Other requirements still needed")

        for block in non_prescribed:
            title = (block.get("title") or "").strip()
            units = block.get("units", {})
            needed = units.get("needed")
            courses = block.get("course_list", [])

            if needed is not None and needed > 0:
                entry = f"- **{title}**: {needed:.0f} credit(s) needed"
            else:
                entry = f"- **{title}**"

            if courses:
                shown = courses[:6]
                entry += f" — choose from: {', '.join(shown)}"
                if len(courses) > 6:
                    entry += f" (and {len(courses) - 6} more options)"

            lines.append(entry)

        if or_group_blocks:
            units = or_group_blocks[0].get("units", {})
            needed = units.get("needed", 6)
            lines.append(
                f"- **Elective Group Requirement**: {needed:.0f} credits needed "
                f"— complete one group in consultation with your advisor"
            )

    # ── In-progress courses ─────────────────────────────────────────────
    if in_progress:
        lines.append("")
        lines.append("### Currently in progress this semester")
        lines.append(", ".join(in_progress))

    # ── Advisor ─────────────────────────────────────────────────────────
    if advisor:
        lines.append("")
        lines.append("### Your advisor")
        lines.append(
            f"Your assigned advisor is **{advisor}**. "
            "Contact them to confirm remaining requirements and plan your final semesters."
        )

    lines.append("")
    lines.append(
        "*This answer is based on the requirement blocks in your uploaded what-if report. "
        "Run your Degree Audit on LionPATH for the most accurate official view.*"
    )

    return "\n".join(lines)


def ask_advisor(question, user_id: str = None):
    intent = detect_question_intent(question)

    retrieved_records = semantic_search(question, top_k=10)
    records = select_top_records(retrieved_records, intent)

    context = build_context_from_records(records)
    rules = extract_requirement_rules(records)
    rule_summary = build_rule_summary(rules)
    sources = build_sources(records)

    student_doc_context = ""
    student_doc = get_current_student_doc(user_id) if (user_id and has_student_doc(user_id)) else {}

    if user_id and has_student_doc(user_id):
        student_doc_context = build_student_doc_context(user_id)

    user_major = get_user_major(user_id) if user_id else None
    program_snippet = build_program_context_snippet(user_major) if user_major else ""

    # Deterministic path first for student-progress questions
    if intent == "student_progress" and student_doc:
        deterministic_answer = build_student_progress_answer(student_doc)
        if deterministic_answer:
            return {
                "answer": deterministic_answer,
                "sources": sources,
                "intent": intent,
                "rule_summary": rule_summary,
                "used_student_doc": True
            }

    system_prompt = f"""
You are ACE, the Academic Counselling Engine for Penn State students.

The student's question intent is: {intent}
{"The student's selected major is: " + user_major if user_major else ""}

You must answer using only:
1. the provided advising records,
2. the extracted rules,
3. the uploaded student academic document if it is provided,
4. the program requirements if provided below.
{program_snippet}

Strict rules:
- Give a direct answer first.
- If courses or requirements are involved, list the actual courses as bullets.
- Section labels such as "Probability and Statistics (6 credits)" should NOT be bullets. They should appear as headings followed by the course options.
- If there are options, alternatives, or either/or choices, show them clearly.
- For either/or requirements, format them like this:
  Either:
  - Option 1
  - Option 2
- Do not split one either/or rule awkwardly across multiple bullets.
- If the student is asking for contact help and the uploaded student document contains a "Student's personally assigned advisor" field, use that advisor name as the primary answer. Only mention general department advisors from the vault records as secondary/alternative contacts.
- If the student is asking about transfer credit or ETM, explain the rule clearly and simply.
- If the records contain explicit rule language such as "may substitute", "can substitute", "may be substituted", "either/or", "required", or "must complete", follow that wording exactly.
- For substitution questions, do not reinterpret the rule. If the records say a course may substitute for another course, answer yes.
- For requirement questions, prioritize explicit requirement rules over vague summaries.
- If a student document is provided and the question is personal, use that document to personalize the answer.
- If the uploaded student document does not contain enough information to answer the personal question, say that clearly.
- Prefer exact handbook rule language when available.
- Do not say "typically", "likely", or "may need" unless the records themselves are uncertain.
- Do not invent requirements, options, policies, emails, contacts, grades, GPA values, or substitutions.
- If the records are incomplete, say that clearly.
- Keep the wording student-friendly and specific.
- Do not mention internal record numbers.
- Do not add generic advice like checking degree audit unless the records specifically support it.
"""

    user_prompt = f"""
Student question:
{question}

Relevant advising records:
{context}

Extracted rule summary:
{rule_summary}

Uploaded student academic document:
{student_doc_context if student_doc_context else "No student document uploaded."}

Write the answer in this style:
1. Start with 1 to 2 sentences directly answering the question.
2. If courses are listed under a requirement heading (for example "Probability and Statistics (6 credits)"), write the heading normally and place the course options under it as bullets.
3. If there is an either/or requirement, write:
   Either:
   - first option
   - second option
4. Keep course requirement bullets clean and specific.
5. If the question is about contact information, clearly list the person or office and how to reach them.
6. If the question is about substitution or replacement, first answer yes or no, then state the exact substitution rule from the records in simple words.
7. If the question is personal and a student document is uploaded, use that document directly.
8. Only use details that appear in the records, extracted rule summary, or uploaded student document.
"""

    try:
        completion = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )

        answer = completion.choices[0].message.content
        record_usage("chat", OPENAI_CHAT_MODEL, completion.usage, user_id=user_id)

        return {
            "answer": answer,
            "sources": sources,
            "intent": intent,
            "rule_summary": rule_summary,
            "used_student_doc": bool(student_doc_context)
        }

    except Exception as e:
        return {
            "answer": "The chatbot could not answer right now. Please check your API key, billing, or quota and try again.",
            "sources": sources,
            "intent": intent,
            "rule_summary": rule_summary,
            "used_student_doc": bool(student_doc_context),
            "error": str(e)
        }


_DECLARED_MAJOR_KEYWORDS = [
    "declared my major",
    "declared the major",
    "my major is",
    "i'm in cmpsc",
    "i'm in cs",
    "i'm a cmpsc",
    "i'm a cs",
    "i am in cmpsc",
    "i am in cs",
    "cmpsc major",
    "cs major",
    "computer science major",
    # DS / DTSCE
    "i'm in dtsce",
    "i'm in ds",
    "i am in dtsce",
    "i am in ds",
    "dtsce major",
    "data sciences major",
    "data science major",
    "computational data sciences",
    "i study data",
    # general
    "in the major",
    "entered the major",
    "admitted to the major",
    "in my major",
    "i study computer",
    "i'm a junior",
    "i'm a senior",
    "i am a junior",
    "i am a senior",
    "junior in",
    "senior in",
]


def detect_declared_major(question, history=None, doc_type=None):
    """Return True if evidence suggests the student has already declared their major."""
    # Transcript always implies enrollment; degree audit implies declared
    if doc_type in ("degree_audit", "transcript"):
        return True

    texts = [question.lower()]
    if history:
        for msg in history[-6:]:
            texts.append(msg.get("content", "").lower())
    combined = " ".join(texts)

    return any(kw in combined for kw in _DECLARED_MAJOR_KEYWORDS)


_DEGREE_AUDIT_FOOTER = (
    "\n\n---\n"
    "> **Note:** This answer is based on your uploaded what-if report. "
    "For the most accurate view of your requirements, run your **Degree Audit** on LionPATH — "
    "what-if reports may not reflect the correct requirements for students who have already declared their major. "
    "[How to run a Degree Audit](https://tutorials.lionpath.psu.edu/public/S_RunningDegreeAudit/)"
)


CAMPUS_RESOURCES_SNIPPET = """
=== PSU CAMPUS RESOURCES (mention only when directly relevant) ===
- Mental health / counseling: CAPS — https://studentaffairs.psu.edu/counseling (free, confidential)
- Crisis support: 988 Lifeline (call/text 988), Crisis Text Line (text HOME to 741741)
- Medical care: UHS — https://studentaffairs.psu.edu/health
- Free tutoring: LRC — https://lrc.psu.edu/
- Writing help: Writing Center — https://writing.psu.edu/
- Calculus help: Calc Central — https://math.psu.edu/undergraduate/calculus-central
- Career & internships: Career Services — https://careerservices.psu.edu/ | Handshake — https://psu.joinhandshake.com/
- Student clubs: OrgCentral — https://orgcentral.psu.edu/
- Campus rec / gym: RecSports — https://recsports.psu.edu/
- Emergency financial aid: https://studentaffairs.psu.edu/student-care/emergency-fund
- Nighttime escort: Safe Walk — https://police.psu.edu/services/safewalk
- Student crisis support: Student Care & Advocacy — https://studentaffairs.psu.edu/student-care
Mention the most relevant 1–2 resources naturally at the end of your response. Do not list all of them.
"""


FINANCIAL_AID_RESOURCES_SNIPPET = """
=== FINANCIAL AID — REFER TO THE OFFICE OF STUDENT AID (do NOT give personalized aid advice) ===
ACE does NOT calculate, estimate, or advise on a student's individual financial aid, eligibility,
amounts, or appeals. Those are personal and handled by the official office. Answer by pointing the
student to the right place and how to reach it:
- Office of Student Aid (primary contact for aid questions): https://studentaid.psu.edu/  | 814-865-6301
- FAFSA — federal aid application (required for most aid): https://studentaid.gov/
- Billing & payment (tuition bills, payment plans): Bursar — https://bursar.psu.edu/
- Scholarships at Penn State: https://studentaid.psu.edu/types-of-aid/scholarships
- Emergency financial help: https://studentaffairs.psu.edu/student-care/emergency-fund
Give the 1–2 most relevant links and tell the student to contact the Office of Student Aid for their
specific situation. Do not quote dollar amounts, eligibility rules, or deadlines from memory.
"""

INTERNATIONAL_RESOURCES_SNIPPET = """
=== INTERNATIONAL STUDENTS / VISA — REFER TO PENN STATE GLOBAL / DISSA (do NOT give immigration advice) ===
ACE is NOT an immigration adviser. Visa and work-authorization matters (F-1, J-1, OPT, CPT, I-20,
SEVIS, travel signatures, maintaining status) are governed by federal law, are individualized, and
wrong guidance can put a student OUT OF STATUS. Do NOT state visa rules, eligibility, timelines, or
deadlines, and do NOT tell the student what to file. Always route them to the official advisers:
- Penn State Global / DISSA (Directorate of International Student & Scholar Advising): https://global.psu.edu/
  — schedule with an international student adviser (DSO/ARO) for any visa/SEVIS/work-authorization question.
- Each campus has a designated international student adviser; University Park is served by Penn State Global.
For non-immigration questions (academics, campus life, English support), help normally — but for anything
touching visa status, your answer is: "that's handled by your international student adviser at Penn State
Global; here's how to reach them." Be warm and reassuring; do not attempt the immigration answer yourself.
"""


_DEADLINES_STATIC_NOTES = """
IMPORTANT NOTES:
- "W" grades (course withdrawals) appear on transcript but do NOT affect GPA.
- Dropping after the late-drop deadline requires Dean's exception (rare — illness, emergency).
- LionPATH is the official system to add/drop courses and view your schedule.
- Late-drop and withdrawal deadlines may differ for module courses and summer sessions.
- Always verify exact dates on the official Registrar's academic calendar.

OFFICIAL LINKS:
- Academic Calendar: https://registrar.psu.edu/academic-calendar/
- Drop/Withdrawal policy: https://registrar.psu.edu/student-records/drop-withdrawal/
- LionPATH (schedule, registration): https://lionpath.psu.edu/
- Schedule of Courses: https://soc.psu.edu/
- Tuition/Billing: https://bursar.psu.edu/
"""

# (today_iso, snippet) — recomputed when the calendar day changes so a
# long-running worker always derives "today" correctly.
_deadlines_cache: tuple[str, str] | None = None


def _semester_date_bounds(sem: dict) -> tuple[str | None, str | None]:
    """(min_iso, max_iso) of a semester's events, or (None, None)."""
    isos = [e["iso_date"] for e in sem.get("events", []) if e.get("iso_date")]
    return (min(isos), max(isos)) if isos else (None, None)


def _build_deadlines_snippet() -> str:
    """
    Build the deadlines snippet from backend/data/calendar.json.

    Picks the CURRENT term from today's date (not the frozen `current_semester`
    baked in at scrape time), and applies a freshness guard: if the file's data
    is entirely in the past, ACE is told NOT to state specific dates and to defer
    to the registrar — so it never confidently emits last term's deadlines.

    Cached per calendar-day.
    """
    global _deadlines_cache
    today_iso = date.today().isoformat()
    if _deadlines_cache is not None and _deadlines_cache[0] == today_iso:
        return _deadlines_cache[1]

    try:
        from backend.services.calendar_scraper import load_calendar
        data = load_calendar()
    except Exception:
        data = None

    def _finish(snippet: str) -> str:
        global _deadlines_cache
        _deadlines_cache = (today_iso, snippet)
        return snippet

    if not data or not data.get("semesters"):
        return _finish(
            "=== PENN STATE ACADEMIC CALENDAR ===\n"
            "(Calendar data unavailable — tell the student you don't have verified "
            "dates and to check https://registrar.psu.edu/academic-calendar/)"
            + _DEADLINES_STATIC_NOTES
        )

    semesters = data.get("semesters", [])
    scraped_at = (data.get("scraped_at") or "")[:10] or "unknown"
    bounded = [(_semester_date_bounds(s), s) for s in semesters]
    latest = max((hi for (_, hi), _ in bounded if hi), default=None)

    # Freshness guard — all events are in the past → don't emit stale dates.
    if latest is not None and latest < today_iso:
        return _finish(
            "=== PENN STATE ACADEMIC CALENDAR — DATA OUT OF DATE ===\n"
            f"ACE's calendar data only runs through {latest}, but today is {today_iso}. "
            "It does NOT have verified dates for the current or upcoming term. Do NOT "
            "state specific deadline dates; tell the student to check the official "
            "calendar at https://registrar.psu.edu/academic-calendar/."
            + _DEADLINES_STATIC_NOTES
        )

    # Relevant terms = ongoing or starting within ~8 months, by start date.
    # (Time-windowed, not index-based, so summer's many sub-sessions don't crowd
    # out the next major term — e.g. a June question still sees Fall.)
    ordered = sorted(bounded, key=lambda b: (b[0][0] or "9999"))
    horizon = (date.today() + timedelta(days=245)).isoformat()
    relevant = [
        sem for (lo, hi), sem in ordered
        if hi and hi >= today_iso and lo and lo <= horizon
    ][:8]
    if not relevant:  # safety net; the freshness guard above usually catches this
        relevant = [sem for _, sem in ordered[:3]]

    lines = [
        "=== PENN STATE ACADEMIC CALENDAR — KEY DEADLINES ===",
        f"(Today is {today_iso}. Calendar data current as of {scraped_at}. If the "
        "student asks about a term not listed below, say you don't have those dates "
        "yet and point them to registrar.psu.edu — do NOT guess.)",
    ]
    for sem in relevant:
        lines.append(f"\n{sem['semester'].upper()}:")
        for ev in sem.get("events", []):
            date_str = ev.get("date", "")
            time_str = ev.get("time", "")
            suffix = f" at {time_str}" if time_str else ""
            lines.append(f"- {ev['event']}: {date_str}{suffix}")

    lines.append(_DEADLINES_STATIC_NOTES)
    return _finish("\n".join(lines))


def _get_deadlines_snippet() -> str:
    return _build_deadlines_snippet()


# Keep the name for backward compatibility — evaluated lazily on first use
def _deadlines_snippet_property() -> str:
    return _get_deadlines_snippet()

DS_GEN_ED_SNIPPET = """
=== PENN STATE GEN ED REQUIREMENTS FOR DTSCE (DATA SCIENCES, 2024-2025) ===

COMMUNICATIONS (9 credits — required for DTSCE):
- ENGL 15 GWS (3) — Rhetoric and Composition (ENGL 30 or ESL 15 may substitute)
- ENGL 202C GWS (3) — Technical Writing
- CAS 100 A/B (3) — Effective Speech
- ENGL/CAS 137 & 138 may substitute for ENGL 15 and CAS 100 A/B

QUANTIFICATION (14 credits — required for DTSCE):
- MATH 140 GQ (4) — Calculus I
- MATH 141 GQ (4) — Calculus II
- MATH 220 GQ (2) — Matrices
- MATH 230 (4) — Calculus and Vector Analysis (MATH 231+232 may substitute)

NATURAL SCIENCES (9 credits):
- Any GN courses except: ASTRO 1/6/7N/10/11/120/140, all BISC, CHEM below 110 (3cr CHEM 106 OK), GAME 180N, PHYS 250/251, PHYS below 211, GEOSC 20

OTHER GENERAL EDUCATION (21 credits):
- Health & Wellness (GHW): 3 credits (or two 1.5-credit courses)
- Arts (GA), Humanities (GH), Social/Behavioral Sciences (GS), US Cultures (US), International Cultures (IL) — same as university-wide Penn State Gen Ed requirements

DOUBLE-DIP OPPORTUNITIES for DTSCE students:
- MATH 140/141: GQ + DTSCE Quantification requirement
- ENGL 15: FYW + DTSCE Communications requirement
- CAS 100: Speaking + DTSCE Communications requirement
- ENGL 202C: GWS + DTSCE Communications requirement

SMART PICKS for DS students:
- STAT 184 (Intro to R, GQ): Direct major requirement — take early
- PHIL 010 (Ethics, GH): Relevant to DS 435 Ethical Issues in Data Science
- ECON 102 (Microeconomics, GS): Useful for data analytics careers
- KINES 082 (Health for Living, GHA): Easy 2-credit online option
- INTL 100 (International Relations, IL): Relevant to global data analytics
"""

GEN_ED_SNIPPET = """
=== PENN STATE GEN ED REQUIREMENTS (2024-2025) ===

Penn State's General Education program requires students to complete courses in these categories:

FOUNDATION REQUIREMENTS (mostly satisfied by CMPSC major requirements):
- First-Year Writing (FYW): ENGL 015 or ENGL 030 (3 cr) — already required for CMPSC
- Quantification (GQ): 3+ credits of math/logic — MATH 140 (required for CMPSC) satisfies this
- Natural Sciences (GN): 6 credits, 2 courses, at least 1 with a lab — PHYS 211 + PHYS 212 (required for CMPSC) satisfy this
- Speaking: CAS 100A, 100B, or 100C (3 cr) — already required for CMPSC
- Writing Across Curriculum (W): Satisfied by CMPSC 431W and CMPSC 483W (required for CMPSC)

KNOWLEDGE DOMAIN REQUIREMENTS (students must select courses):
- Arts (GA): 3 credits — e.g., MUSC 007, MUSC 008, THEA 100, ART 010, ENGL 200N
- Humanities (GH): 3 credits — e.g., PHIL 010 (Ethics, highly recommended for CS), PHIL 012 (Logic), HIST 021, LING 100
- Social & Behavioral Sciences (GS): 3 credits — e.g., PSYCH 100, ECON 102, SOC 001, COMM 100
- Health & Physical Activity (GHA): 2 credits — e.g., KINES 082 (Health for Living, popular online option)
- United States Cultures (US): 3 credits — e.g., HIST 026, WMNST 001, SOC 119, AFAM 100
- International Cultures (IL): 3 credits — e.g., ANTH 001, INTL 100, GEOG 020, foreign language intermediate courses

DOUBLE-DIP OPPORTUNITIES (courses satisfying both Gen Ed AND major requirements):
- MATH 140: GQ + CMPSC major requirement
- PHYS 211 + PHYS 212: GN + CMPSC major requirement
- ENGL 015/030: FYW + CMPSC major requirement
- CAS 100A/B/C: Speaking + CMPSC major requirement
- CMPSC 431W, 483W: Writing (W) + CMPSC major requirement
- HIST 021: Can satisfy both GH and US (check current designation)
- SOC 119: Can satisfy both GS and US

SMART PICKS FOR CS STUDENTS:
- PHIL 010 (Ethics, GH): Directly relevant to AI ethics, software engineering ethics, and tech policy
- ECON 102 (Microeconomics, GS): Great for product thinking, startups, tech business understanding
- KINES 082 (Health for Living, GHA): Popular 2-credit online course, easy checkbox
- MUSC 008 (History of Rock, GA): Low-stress creative requirement, great balance to CS workload
- INTL 100 (International Relations, IL): Relevant for international tech careers and global perspective
- LING 100 (Language & Linguistics, GH): Surprisingly relevant to CS (parsing, syntax, NLP)
- ECON 104 (Macroeconomics, GS): Complements ECON 102 for broader economic understanding

IMPORTANT RULES:
- GN requires at least one course to have a lab component
- Many courses carry multiple designations — always check the Schedule of Courses for current designations
- Gen Ed requirements may vary slightly by catalog year — verify on LionPATH or with your advisor
- US and IL requirements emphasize diversity perspectives; check if your preferred course carries the designation

Official source: https://bulletins.psu.edu/undergraduate/general-education/
"""


NEUTRAL_GEN_ED_SNIPPET = """
=== PENN STATE GENERAL EDUCATION (university-wide, 2024-2025) ===

Every Penn State undergraduate completes Gen Ed across these categories
(specific credit counts and overlaps vary by major):

FOUNDATIONS:
- First-Year Writing (FYW): e.g. ENGL 015 or ENGL 030 (3 cr)
- Quantification (GQ): math/logic/quantitative reasoning (6 cr)
- Speaking / Writing-Across-the-Curriculum where required by the major

KNOWLEDGE DOMAINS (students choose courses that carry the designation):
- Arts (GA): 3 credits
- Humanities (GH): 3 credits
- Social & Behavioral Sciences (GS): 3 credits
- Natural Sciences (GN): 6 credits (at least one course with a lab)
- Health & Wellness (GHW): 3 credits (or two 1.5-cr courses)
- United States Cultures (US): 3 credits
- International Cultures (IL): 3 credits

KEY RULES:
- Many courses carry more than one designation — check the Schedule of Courses
  for current designations, and look for courses that "double-dip" with the
  student's own major requirements.
- Exact Gen Ed credit totals and which major courses overlap depend on the
  student's specific program — direct them to LionPATH or their advisor, or to
  select their major in ACE for tailored Gen Ed guidance.

Official source: https://bulletins.psu.edu/undergraduate/general-education/
"""


def _build_dynamic_gen_ed_snippet(program_name: str, prog: dict | None, double_dips: list[dict]) -> str:
    """Build a gen-ed context snippet from live program data."""
    lines = [f"=== PENN STATE GEN ED — {program_name.upper()} ==="]
    if prog:
        overlap = prog.get("gen_ed_overlap", {})
        overlap_note = prog.get("gen_ed_overlap_note", "")
        if overlap_note:
            lines.append(overlap_note)
        elif overlap:
            parts = ", ".join(f"{v} credits of {k}" for k, v in overlap.items())
            lines.append(f"Gen Ed overlap with this major: {parts}")

    if double_dips:
        lines.append("")
        lines.append("DOUBLE-DIP OPPORTUNITIES (courses satisfying both this major AND Gen Ed):")
        for dd in double_dips:
            cats = ", ".join(dd.get("gen_ed_categories", []))
            tag = "Prescribed" if dd.get("is_prescribed") else "Elective option"
            lines.append(f"  - {dd['code']} ({dd.get('credits','')} cr) — Gen Ed: {cats} [{tag}]")

    lines.append("")
    lines.append("Use the above program-specific Gen Ed overlap data to answer the student's question accurately.")
    return "\n".join(lines)


def build_degree_audit_advisory(doc_type, declared):
    """Return a system-prompt advisory string, or empty string."""
    # Always advise when a what-if is uploaded
    if doc_type == "what_if_report":
        return (
            "\n\n=== DEGREE AUDIT ADVISORY ===\n"
            "The student has uploaded a what-if report. Answer their question using that report, "
            "then always end your response with a brief note recommending they use the Degree Audit "
            "on LionPATH for more accurate results, because what-if reports may not show the correct "
            "requirements for students who have declared their major. "
            "Link: https://tutorials.lionpath.psu.edu/public/S_RunningDegreeAudit/"
        )

    # Softer suggestion when declared is detected via text but no doc (or unknown doc)
    if declared and doc_type in (None, "academic_document"):
        return (
            "\n\n=== DEGREE AUDIT ADVISORY ===\n"
            "Evidence in this conversation suggests the student has already declared their major. "
            "If they ask about tracking requirements or remaining courses, recommend using the "
            "Degree Audit on LionPATH rather than a what-if report."
        )

    return ""


def ask_advisor_stream(question, history=None, user_id: str = None, major: str = None):
    """Generator that yields SSE-formatted chunks for the chat response.

    history: list of {"role": "user"|"assistant", "content": str} dicts
             representing the prior conversation turns.
    user_id: Clerk user ID of the signed-in student; used to look up their
             uploaded document and (if `major` is not given) their major.
    major:   Optional explicit program name to ground on, bypassing the DB
             lookup. Used by the eval harness to test a major without a
             persisted user. Falls back to the user's stored major when None.
    """
    intent = detect_question_intent(question)
    user_major = major or (get_user_major(user_id) if user_id else None)
    major_kind = classify_major(user_major)        # 'cs' | 'ds' | 'other' | None
    structured_only = major_kind == "other"
    # The RAG index is 100% CMPSC/DTSCE. We only let it drive the answer for
    # declared CS/DS students. For any other major ('other') AND for students
    # with no major at all (None), we keep those records out so the model does
    # not silently treat the student as a CS/DS student.
    suppress_cs_ds = major_kind in (None, "other")
    logger.info(
        "ask_advisor_stream | intent=%r | major=%r (%s) | question=%r",
        intent, user_major, major_kind or "none", question[:80],
    )

    if suppress_cs_ds:
        records = []
        rule_summary = ""
        if structured_only:
            # Has a known program — ground on its programs.json requirements.
            context = (
                "(No indexed handbook records exist for this program. Use the "
                "PROGRAM REQUIREMENTS section below as the authoritative source.)"
            )
            sources = build_program_sources(user_major)
        else:
            # No major declared — stay neutral, no program to cite.
            context = (
                "(The student has not selected a major, so no major-specific "
                "records are available. Do not assume any particular program.)"
            )
            sources = []
    else:
        retrieved_records = semantic_search(question, top_k=10)
        records = select_top_records(retrieved_records, intent)
        logger.debug("ask_advisor_stream | retrieved=%d selected=%d", len(retrieved_records), len(records))
        context = build_context_from_records(records)
        rules = extract_requirement_rules(records)
        rule_summary = build_rule_summary(rules)
        sources = build_sources(records)

    student_doc_context = ""
    student_doc = get_current_student_doc(user_id) if (user_id and has_student_doc(user_id)) else {}

    if user_id and has_student_doc(user_id):
        student_doc_context = build_student_doc_context(user_id)

    doc_type = student_doc.get("doc_type") if student_doc else None
    declared = detect_declared_major(question, history, doc_type)
    degree_audit_advisory = build_degree_audit_advisory(doc_type, declared)
    if degree_audit_advisory:
        logger.info("ask_advisor_stream | degree audit advisory injected | doc_type=%r", doc_type)

    resources_snippet = CAMPUS_RESOURCES_SNIPPET if intent == "wellbeing" else ""
    deadline_snippet = _get_deadlines_snippet() if intent == "deadline" else ""
    aid_snippet = FINANCIAL_AID_RESOURCES_SNIPPET if intent == "financial_aid" else ""
    intl_snippet = INTERNATIONAL_RESOURCES_SNIPPET if intent == "international" else ""

    # Build program requirements context if user has a major selected
    program_snippet = ""
    if user_major:
        try:
            program_snippet = build_program_context_snippet(user_major)
        except Exception:
            pass

    # For structured-only majors, steer the model onto the program data and off
    # the CS/DS framing the rest of the index is built around.
    major_guidance = ""
    if structured_only:
        college = ""
        try:
            college = (get_program(user_major) or {}).get("college", "").replace("-", " ")
        except Exception:
            pass
        if not program_snippet:
            logger.warning("ask_advisor_stream | structured-only major has no program data: %r", user_major)
        major_guidance = (
            f"\n\nMAJOR-SPECIFIC GROUNDING (important):\n"
            f"- The student's major is {user_major}. No Computer Science or Data Sciences "
            f"records are relevant here.\n"
            f"- Answer course and requirement questions using ONLY the PROGRAM REQUIREMENTS "
            f"section below. Never mention CMPSC or DTSCE courses/requirements unless the "
            f"student explicitly asks about them.\n"
            f"- For advisor or contact questions, point the student to their college's advising "
            f"office" + (f" ({college})" if college else "") + " and the advisor named in their "
            f"uploaded document if one is present.\n"
            f"- If the PROGRAM REQUIREMENTS section lacks the detail needed, say so plainly and "
            f"suggest they confirm on the Penn State Bulletin or with their advisor."
        )
    elif major_kind is None:
        # No major declared: do NOT default to CS/DS framing.
        major_guidance = (
            "\n\nNO MAJOR SELECTED (important):\n"
            "- The student has not told us their major. Do NOT assume they study Computer "
            "Science or Data Sciences, and do NOT describe yourself as a CS/DS advisor.\n"
            "- Answer university-wide questions (deadlines, policies, general Gen Ed, campus "
            "resources) directly.\n"
            "- For anything that depends on a specific major (required courses, a degree plan), "
            "give general guidance and invite the student to select their major — or upload "
            "their What-If / Degree Audit — so you can tailor the answer.\n"
            "- Never reference CMPSC or DTSCE courses/requirements unless the student explicitly asks."
        )

    # Gen-ed snippet: prefer the student's own program data. Only fall back to
    # the CMPSC/DTSCE static tables for declared CS/DS students — everyone else
    # (other major or no major) gets the neutral university-wide block.
    if intent == "gen_ed":
        if user_major:
            try:
                double_dips = get_double_dips(user_major)
                prog = get_program(user_major)
                gen_ed_snippet = _build_dynamic_gen_ed_snippet(user_major, prog, double_dips)
            except Exception:
                gen_ed_snippet = (
                    GEN_ED_SNIPPET if major_kind == "cs"
                    else DS_GEN_ED_SNIPPET if major_kind == "ds"
                    else NEUTRAL_GEN_ED_SNIPPET
                )
        else:
            gen_ed_snippet = NEUTRAL_GEN_ED_SNIPPET
    else:
        gen_ed_snippet = ""

    # Deterministic path — stream the full answer as one chunk then done
    if intent == "student_progress" and student_doc:
        deterministic_answer = build_student_progress_answer(student_doc)
        if deterministic_answer:
            logger.info("ask_advisor_stream | using deterministic path")
            if doc_type == "what_if_report":
                deterministic_answer += _DEGREE_AUDIT_FOOTER
            yield f"data: {json.dumps({'text': deterministic_answer})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': sources, 'intent': intent, 'used_student_doc': True})}\n\n"
            return

    # All context lives in the system prompt so history messages stay lightweight
    system_prompt = f"""You are ACE, the Academic Counselling Engine for Penn State University students.
The detected intent for the current question is: {intent}
{"The student's selected major is: " + user_major if user_major else ""}{major_guidance}

=== ADVISING RECORDS (current question) ===
{context}

=== EXTRACTED RULES ===
{rule_summary}

=== STUDENT DOCUMENT ===
{student_doc_context if student_doc_context else "No student document uploaded."}{degree_audit_advisory}{program_snippet if program_snippet else ""}{resources_snippet}{deadline_snippet}{aid_snippet}{intl_snippet}{gen_ed_snippet}

=== ANSWER RULES ===
- You may use the conversation history above to understand follow-up context, but ground every answer in the advising records, extracted rules, and student document provided.
- Give a direct answer first (1–2 sentences).
- List courses as bullets. Do NOT bullet section labels (e.g. "Probability and Statistics (6 credits)") — use them as headings.
- For either/or requirements use exactly:
  Either:
  - Option A
  - Option B
- For contact questions, use the advisor name from the student document first; only mention department contacts as secondary.
- Quote exact handbook language when available. Do not say "typically" or "likely" unless the records themselves are uncertain.
- Never invent courses, policies, contacts, grades, or substitutions not present in the records.
- If records are insufficient, say so clearly.
- Do not mention internal record numbers.
- If a Degree Audit Advisory is present above, include the recommendation naturally in your answer when it is relevant to what the student asked.
- Keep the tone student-friendly and specific.
"""

    try:
        # Build messages: system → history (capped at 6) → current question
        messages_list = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history[-6:]:
                messages_list.append({"role": msg["role"], "content": msg["content"]})

        messages_list.append({"role": "user", "content": question})

        logger.info("ask_advisor_stream | calling OpenAI model=%r messages=%d", OPENAI_CHAT_MODEL, len(messages_list))
        stream = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=messages_list,
            temperature=0.0,
            stream=True,
            stream_options={"include_usage": True},
        )

        usage = None
        for chunk in stream:
            if getattr(chunk, "usage", None) is not None:
                usage = chunk.usage  # final chunk carries token usage
            if chunk.choices and chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"

        record_usage("chat", OPENAI_CHAT_MODEL, usage, user_id=user_id)
        logger.info("ask_advisor_stream | stream complete | sources=%d", len(sources))
        yield f"data: {json.dumps({'done': True, 'sources': sources, 'intent': intent, 'used_student_doc': bool(student_doc_context)})}\n\n"

    except Exception as e:
        logger.error("ask_advisor_stream | error: %s", e, exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True, 'sources': [], 'intent': intent})}\n\n"