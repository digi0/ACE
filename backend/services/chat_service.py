import logging
import re
import json
from datetime import date, timedelta
from dotenv import load_dotenv
from backend.services import llm
from backend.services.embedding_service import semantic_search
from backend.services.student_doc_service import (
    has_student_doc,
    build_student_doc_context,
    get_current_student_doc,
    get_user_major,
)
from backend.services.program_service import (
    get_program,
    get_prerequisites,
    build_program_context_snippet,
    build_recommendation_context,
    get_double_dips,
)
from backend.services.policy_service import build_policy_snippet, policy_sources
from backend.services.transcript_service import save_exchange
from backend.services.profile_service import build_profile_snippet, remember, get_profile
from backend.services.clubs_service import build_clubs_snippet, search_clubs
from backend.services.procedures_service import build_procedures_snippet, find_procedures
from backend.services.places_service import build_places_snippet, find_places
from backend.services.events_service import (
    build_events_snippet, find_events, mentions_events, is_stale as is_events_stale,
)
from backend.services.money_service import build_money_snippet, find_money
from backend.services.visual_policy import decide as decide_visual, build_visual_directive

load_dotenv()

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
    # Catches the phrasings the two above miss ("what things do I need to
    # graduate?"), which otherwise fell through to a generic requirement dump.
    "need to graduate",
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


    # Gen-ed category codes are two-letter tokens that also live inside ordinary
    # words: "sign up" contains "gn ", "things" contains "gs ", "through"
    # contains "gh ". As bare substrings they routed "how do things work here?"
    # to gen_ed. Match them as standalone tokens, same as the ap/ib fix above.
    gen_ed_code = re.search(r"\b(ga|gh|gq|gn|gs|gha|ghw|gws|il)\b", q)

    gen_ed_keywords = [
        "gen ed", "general education", "gened", "us culture",
        "international culture", "il course", "arts requirement",
        "humanities requirement", "social science requirement",
        "natural science requirement", "quantification", "health requirement",
        "diversity requirement", "writing requirement", "speaking requirement",
        "gen ed requirement", "gen-ed", "general ed",
        "what counts for", "what satisfies", "double dip", "double-dip",
        "kines 082", "phil 010", "musc 007", "musc 008", "thea 100",
        "psych 100", "econ 102", "anth 001", "intl 100",
    ]

    # How the machine works, as opposed to when it happens. "How do I register"
    # and "when does registration open" are different questions with different
    # answers; both used to land on `deadline` and get a wall of dates. Keep
    # these phrases specific — bare "registration" belongs to deadline.
    logistics_keywords = [
        "how do i register", "how to register", "how does registration work",
        "how do i enroll", "how to enroll", "how does enrollment work",
        "how do i sign up for class", "how do i add a class", "how do i drop a class",
        "how do i swap", "how do i pick classes", "how do i choose classes",
        "how do i build my schedule", "how do i get into a class",
        "registration hold", "advising hold", "hold on my account", "clear my hold",
        "lionpath", "lion path", "student center", "course cart", "schedule builder",
        "enrollment appointment", "registration appointment", "registration window",
        "orientation", "new student", "just enrolled", "just got accepted",
        "just committed", "just started", "what do i do first", "where do i start",
        "first steps", "waitlist", "wait list", "closed section", "class is full",
        "how do i see my schedule", "how do i find my classes",
    ]

    # Asking ACE to propose, not to recite. These get a plan, not a requirement
    # dump — see the recommendation grounding in ask_advisor_stream.
    recommendation_keywords = [
        "what should i take", "what should i sign up", "what should i register",
        "what classes should i", "what courses should i", "which classes should i",
        "which courses should i", "what do you recommend", "what would you suggest",
        "recommend a course", "recommend classes", "recommend courses",
        "course recommendation", "suggest a schedule", "suggest classes",
        "suggest courses", "suggest a course", "build me a schedule",
        "plan my semester", "plan my next semester", "help me plan",
        "how many credits should i take", "good course load", "what's a good schedule",
    ]
    # "recommend"/"suggest" on their own are too broad ("suggest an advisor"), so
    # require them to be about coursework.
    proposes_courses = bool(
        re.search(r"\b(recommend|suggest|advise)\b", q)
        and re.search(r"\b(class|classes|course|courses|schedule|semester|term|credits?)\b", q)
    )

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

    # Distress and support. The short tokens here were the worst offenders in the
    # whole router: "org" lives inside "organic", "rec" inside "record", "broke"
    # inside "broken", so "do I need organic chemistry?" was answered out of the
    # CAPS / 988 crisis block. Bare "health" is gone too — "health requirement"
    # is the GHW gen-ed category, not a wellbeing question.
    wellbeing_keywords = [
        "stress", "stressed", "anxiety", "anxious", "overwhelmed", "burnout",
        "mental health", "depressed", "depression", "struggling", "counseling",
        "student health", "health center", "therapy", "therapist", "crisis",
        "emergency fund", "financial hardship", "can't afford", "cannot afford",
        "safe walk", "unsafe", "harassed", "emergency", "campus police",
        # How someone in trouble actually types it. All of these routed to
        # `general` and got a generic answer instead of the care resources —
        # the one place a miss costs more than a bad answer.
        "losing it", "falling apart", "can't keep up", "cant keep up",
        "drowning", "barely holding", "can't cope", "cant cope", "at my limit",
        "breaking point", "want to give up", "giving up", "behind on everything",
        "spiraling", "spiralling", "panicking", "panic attack", "crying",
        "too much going on", "can't do this", "cant do this",
        "recreation", "recsports", "intramural", "writing center", "tutoring",
        "calculus help",
    ]
    wellbeing_token = re.search(r"\b(caps|uhs|lrc|gym|sick|broke)\b", q)

    # Ring 3 — career, activities, research. These used to live in the wellbeing
    # list, so "how do I find an internship?" was answered from a block that
    # opens with counselling and the 988 crisis line. Checked AFTER wellbeing, so
    # "I'm stressed about finding a job" still routes to support.
    career_keywords = [
        "career", "internship", "internships", "co-op", "cooperative education",
        "resume", "résumé", "cover letter", "handshake", "job", "jobs",
        "employer", "hiring", "linkedin", "networking", "career fair",
        "club", "clubs", "student org", "orgcentral", "extracurricular",
        "get involved", "should i join", "what to join", "somewhere to belong",
        "meet people", "find my people", "research opportunity", "undergraduate research",
        "research lab", "work in a lab", "study abroad", "volunteer",
        "grad school", "graduate school", "portfolio",
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

    # Logistics before deadline: "how do I register" is a steps question, and
    # deadline owns bare "registration"/"register", so it would swallow it.
    if any(keyword in q for keyword in logistics_keywords):
        return "logistics"

    if any(keyword in q for keyword in deadline_keywords):
        return "deadline"

    # Before courses/gen_ed, both of which match "take"/"class" and would turn a
    # request for a proposal into a requirement recital.
    if proposes_courses or any(keyword in q for keyword in recommendation_keywords):
        return "recommendation"

    if gen_ed_code or any(keyword in q for keyword in gen_ed_keywords):
        return "gen_ed"

    if wellbeing_token or any(keyword in q for keyword in wellbeing_keywords):
        return "wellbeing"

    if any(keyword in q for keyword in career_keywords):
        return "career"

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


def filter_records_by_scope(records, major_kind):
    """Keep only the records belonging to the student's own program.

    The index holds CMPSC and DTSCE material side by side, so without this a CS
    student can be answered from — and cited to — the Data Sciences handbook.
    Falls back to the unfiltered set rather than answering from nothing.
    """
    if major_kind not in ("cs", "ds"):
        return records

    marker = "cmpsc" if major_kind == "cs" else "dtsce"
    scoped = [r for r in records if marker in str(r.get("source_name", "")).lower()]
    return scoped or records


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


# Ring 3 (career + activities) is the roadmap ring: ACE has no dataset of clubs,
# labs, employers, or postings. Asked "what clubs should I join as a CS major?"
# it used to answer from the model's own memory — four named organisations with
# confident descriptions, none of them grounded in anything ACE holds. Inventing
# an institution's student organisations is the same failure as inventing a
# course, and harder for a student to catch.
#
# So this block does two jobs: route to the systems that DO hold the data, and
# forbid naming specifics ACE cannot see.
CAREER_RESOURCES_SNIPPET = """
=== CAREER, CLUBS & RESEARCH — REFER, DO NOT INVENT ===

ACE has NO data on student organisations, labs, employers, job postings, or
application deadlines. It cannot see which clubs exist, which are active, who
is hiring, or what any of them require.

WHERE THE REAL DATA LIVES:
- Jobs, internships, career fairs, resume help: Career Services —
  https://careerservices.psu.edu/ and Handshake — https://psu.joinhandshake.com/
- Student organisations, clubs, getting involved: OrgCentral —
  https://orgcentral.psu.edu/ (searchable by interest — this is where the
  student finds the current list)
- Research with faculty: the student's own department, and their academic
  adviser, who knows which faculty take undergraduates.

RULES FOR THIS TOPIC — these override the general answer rules:
- If a MATCHING PENN STATE STUDENT ORGANISATIONS section appears below, those
  organisations are real and came from ACE's own directory — name them, describe
  them, and give their links. That section is the ONLY source of organisation
  names you may use.
- Otherwise do NOT name specific clubs, student organisations, labs, faculty,
  companies, or job postings. Not even ones you believe exist. Send the student
  to OrgCentral or Career Services to see the current, real list.
- You MAY be specific about the student's own academic record — their major,
  the courses they have completed, and what their program's plan contains —
  because that is grounded above. Use it to make the answer about them: what
  their coursework already prepares them for, and what to search for.
- You MAY describe the general shape of the process (when recruiting happens,
  what a career fair is, that research usually starts by contacting faculty).
- Be encouraging and concrete about the NEXT ACTION, not about names you cannot
  verify. "Search OrgCentral for computing and data groups" is a good answer.
  "Join ACM and HackPSU" is not — ACE cannot confirm either exists.
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


# Intents the handbook genuinely serves. Everything else is answered by the
# structured datasets, and pulling handbook chunks in only dilutes the prompt.
# `contact` is deliberately NOT here: it covers both "who is my academic
# adviser" (handbook) and "who do I email about this charge" (bursar). It falls
# through to the no-other-grounding test, which picks correctly for each.
_HANDBOOK_INTENTS = {"etm", "transfer", "substitution"}
# Questions where citing the student's own program bulletin makes sense.
_ACADEMIC_INTENTS = {"courses", "gen_ed", "student_progress", "recommendation"}


def _has_other_grounding(question, intent, user_major) -> bool:
    """True when a structured dataset already answers this, so the handbook is
    not needed as a fallback. Cheap local lookups only."""
    try:
        if find_procedures(question) or find_places(question) or find_money(question):
            return True
        if mentions_events(question) and not is_events_stale() and find_events(question):
            return True
        if intent == "career" and (
            search_clubs([question])
            or (search_clubs([user_major.split(",")[0]]) if user_major else [])
        ):
            return True
        if intent in ("recommendation", "gen_ed", "courses", "student_progress") and user_major:
            return True
        if intent in ("logistics", "deadline", "wellbeing", "financial_aid", "international"):
            return True
    except Exception as exc:  # noqa: BLE001 — never break an answer over this
        logger.warning("_has_other_grounding | %s", exc)
    return False


def _count_visual_material(question, intent, user_major, student_doc, history=None):
    """How many items each visual block would actually have to work with.

    All local lookups — JSON and dict reads, no API calls — so this is cheap to
    run on every request. The point is that the policy can never authorise a
    block that has nothing behind it.
    """
    counts = {}
    try:
        procs = find_procedures(question)
        if procs:
            counts["checklist"] = max(len(p.get("steps") or []) for p in procs)

        places = find_places(question)
        # Mirror build_clubs_snippet's own fallback: question first, then the
        # student's major. Without it the counter said "no cards" while the
        # snippet was happily listing six clubs — the policy and the grounding
        # disagreed about what data existed.
        clubs = []
        if intent == "career":
            clubs = search_clubs([question]) or (
                search_clubs([user_major.split(",")[0]]) if user_major else []
            )
        cards = len(places) + len(clubs)
        if cards:
            counts["cards"] = cards

        if intent in ("deadline", "logistics"):
            counts["strip"] = _upcoming_deadline_count()

        # Events were never counted, so "what's happening this week" could not
        # reach a block no matter how many events the snippet had found.
        if mentions_events(question) and not is_events_stale():
            found = find_events(question)
            if found:
                counts["cards"] = max(counts.get("cards", 0), len(found))

        if user_major and intent in ("recommendation", "student_progress"):
            audit = (student_doc or {}).get("audit_parse") or {}
            done = [c.get("code") for c in audit.get("completed_courses", []) if c.get("code")]
            ctx = build_recommendation_context(user_major, done)
            if ctx and ctx.get("propose"):
                counts["plan"] = len(ctx["propose"])

        # A prereq map only makes sense when a course is on the table — but
        # "map out the prereqs for these classes" names none, because the courses
        # were named a turn ago. Fall back to the recent conversation so anaphora
        # ("these", "them", "that one") still finds something to draw.
        codes = extract_course_codes(question)
        if not codes and history:
            recent = " ".join(m.get("content", "") for m in history[-6:])
            codes = extract_course_codes(recent)
        for code in codes[:1]:
            prereqs = get_prerequisites(code)
            if prereqs:
                counts["map"] = len(prereqs) + 1
    except Exception as exc:  # noqa: BLE001 — counting must never break an answer
        logger.warning("_count_visual_material | %s", exc)
    return counts


def _upcoming_deadline_count() -> int:
    """Dated events left in the current term — the strip's raw material."""
    try:
        from backend.services.calendar_scraper import load_calendar
        today = date.today().isoformat()
        data = load_calendar() or {}
        for sem in data.get("semesters", []):
            future = [e for e in sem.get("events", []) if (e.get("iso_date") or "") >= today]
            if future:
                return len(future)
    except Exception:  # noqa: BLE001
        pass
    return 0


def _build_recommendation_snippet(program_name, student_doc):
    """Grounding for "what should I take next semester?".

    ACE's other answers recite what is required. This one proposes: it locates
    the student in their own plan, lists what is actually outstanding, and flags
    prerequisites they have not met yet. Everything proposed comes from the
    program's own suggested plan — the model is never asked to invent a schedule.
    """
    audit = (student_doc or {}).get("audit_parse") or {}
    completed = [c.get("code") for c in audit.get("completed_courses", []) if c.get("code")]

    ctx = build_recommendation_context(program_name, completed)
    if not ctx:
        return (
            "\n\n=== COURSE RECOMMENDATION ===\n"
            f"ACE has no suggested academic plan on file for {program_name}. Do NOT "
            "invent a schedule. Say plainly that you don't have a plan for this "
            "program yet, answer with the requirements you do have above, and send "
            "the student to their adviser to build the actual schedule."
        )

    lines = ["\n\n=== COURSE RECOMMENDATION ===",
             f"Suggested plan on file: {ctx['plan_label']}"]

    if ctx.get("complete"):
        lines.append(
            "Every course in the suggested plan is already complete in the student's "
            "audit. Congratulate them, and point them to their adviser to confirm "
            "graduation clearance rather than proposing more coursework."
        )
        return "\n".join(lines)

    if ctx.get("personalised"):
        lines.append(
            f"Based on the audit, the student is at: {ctx['position']}. "
            "Courses already completed have been excluded."
        )
    else:
        lines.append(
            f"No audit uploaded, so this is the start of the plan ({ctx['position']}) "
            "— correct for a new student. Offer to personalise it if they upload "
            "their degree audit, but answer the question first."
        )

    lines.append("\nOUTSTANDING SLOTS TO PROPOSE FROM (one course per slot):")
    for c in ctx["propose"]:
        cr = f" ({c['credits']} cr)" if c.get("credits") else ""
        title = f" — {c['title']}" if c.get("title") else ""
        alts = c.get("alternatives") or []
        alt = f"  [or instead: {', '.join(alts)}]" if alts else ""
        blocked = c.get("unmet_prereqs")
        flag = f"  [NOT YET ELIGIBLE — needs {', '.join(blocked)} first]" if blocked else ""
        lines.append(f"  - {c['code']}{title}{cr}{alt}{flag}")

    lines.append(
        "\nANSWERING RULES FOR THIS TOPIC:\n"
        "- Propose an actual slate of courses from the list above, and total the credits.\n"
        "- Each line above is ONE slot. Where alternatives are shown, pick one and "
        "mention the alternative — never propose a slot's alternatives as extra courses.\n"
        "- A course marked NOT YET ELIGIBLE must not be proposed for next semester. "
        "Name the prerequisite the student needs first instead.\n"
        "- Say why the slate makes sense (it is the next block of their plan).\n"
        "- Propose ONLY courses from the list above. Never invent a course, a "
        "section, a time, or a credit count.\n"
        "- Close by telling them to confirm with their adviser and check the "
        "Schedule of Courses for what is actually offered."
    )
    return "\n".join(lines)


# The "how the machine works" bracket. The academic calendar covers WHEN things
# happen (54 registration events) but has zero entries for orientation, holds, or
# the enrollment steps themselves, so this is the only grounding for HOW.
#
# Deliberately describes the SHAPE of each process and routes to the office that
# owns it, rather than asserting click-by-click steps that change every year.
# The closing rule matters more than the content: a confidently invented step
# sends a student to the wrong place, which is worse than "I don't have that".
LOGISTICS_SNIPPET = """
=== PENN STATE LOGISTICS — HOW ENROLLMENT AND REGISTRATION WORK ===

LIONPATH is the student information system. Registration, schedules, holds,
grades, and bills all live there: https://lionpath.psu.edu/
The Schedule of Courses (what is actually offered and when): https://soc.psu.edu/

REGISTERING FOR CLASSES — the shape of it:
1. Registration opens per student on an assigned enrollment/registration
   appointment (a start time, not a single day). Students with more credits
   register earlier. The student's own appointment time is shown in LionPATH.
2. Holds must be cleared BEFORE the appointment, or registration is blocked.
   Common ones are advising holds (see your adviser), bursar/financial holds
   (pay or arrange the balance), and health/immunization holds. LionPATH shows
   which hold is active and which office to contact.
3. Courses are chosen from the Schedule of Courses and added in LionPATH.
4. Registration stays open through the add/drop period at the start of term —
   the exact dates are in the academic calendar section if present above.

WHEN A CLASS IS FULL: LionPATH offers a waitlist for many sections. Being on a
waitlist is not a guarantee, and it does not itself resolve a time conflict or a
missing prerequisite. If the section stays closed, the routes are a different
section, a different course that meets the same requirement, or asking the
department that owns the course about a capacity override.

NEW STUDENTS: orientation and the first-semester schedule are run by New Student
Orientation together with the student's academic college/campus advising office.
New students are commonly advised or scheduled into their first courses through
that process rather than registering unaided.

WHO OWNS WHAT:
- Registration mechanics, records, calendar → Registrar: https://registrar.psu.edu/
- Course requirements and what to take → the student's academic adviser
- Bills, payment holds → Bursar: https://bursar.psu.edu/
- What is offered and when → Schedule of Courses: https://soc.psu.edu/

ANSWERING RULES FOR THIS TOPIC:
- Give the student the sequence and name the office that owns the step.
- Specific dates come only from the academic calendar section above. If it is not
  there, say you don't have the date and link the registrar's calendar.
- Do NOT invent menu names, button labels, exact click paths, or campus-specific
  procedures. If the exact step isn't above, say what the student should look for
  and who to ask. Being honest about the gap beats sending them somewhere wrong.
"""

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
            title = dd.get("title", "")
            lines.append(
                f"  - {dd['code']}{' — ' + title if title else ''}"
                f" ({dd.get('credits','')} cr) — Gen Ed: {cats} [{tag}]"
            )

    # The program data says what overlaps; it never says what the categories ARE.
    # A student asking "which gen eds do I still need?" needs both.
    lines.append(NEUTRAL_GEN_ED_SNIPPET)
    lines.append(
        "Answer using BOTH blocks: the university-wide categories are what the "
        "student still has to satisfy, and the program data above says which of "
        "them their major already covers. For each course you name, say which Gen "
        "Ed category it fills AND how it counts for the major — 'Prescribed' means "
        "it is a required major course, 'Elective option' means it counts only if "
        "the student picks it for that requirement. Write it in plain sentences; "
        "never copy the bracketed tags above verbatim. This student has already "
        "selected their major — do not tell them to select one."
    )
    return "\n".join(lines)


# Extra answer rules appended for intents where a bare fact isn't a useful
# answer. A drop date with no "regular vs late drop" and no "do it in LionPATH"
# leaves the student still not knowing what to do.
_INTENT_ANSWER_RULES = {
    "deadline": (
        "- Deadline answers must be actionable, not just a date: distinguish the "
        "regular drop deadline from the late-drop deadline, name the term you are "
        "quoting, say the student does it in LionPATH, and link the official "
        "calendar (https://registrar.psu.edu/academic-calendar/). Mention that a "
        "late drop shows a 'W' on the transcript but does not affect GPA when the "
        "student is asking about dropping.\n"
    ),
}


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


def ask_advisor_stream(question, history=None, user_id: str = None, major: str = None,
                       conversation_id: str = None):
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

    # The handbook index is 73 chunks of CMPSC/DTSCE procedure. It exists for the
    # things the structured data lacks — entrance-to-major, petitions,
    # substitutions, department contacts — and for nothing else. It used to load
    # on EVERY question a CS/DS student asked, so "where can I eat on campus"
    # arrived with 3,855 tokens of handbook competing with the 693-token answer,
    # and came back citing the handbook. The launch cohort got the worst prompts
    # in the product precisely because they were the only ones with an index.
    use_handbook = not suppress_cs_ds and (
        intent in _HANDBOOK_INTENTS or not _has_other_grounding(question, intent, user_major)
    )
    logger.info(
        "ask_advisor_stream | intent=%r | major=%r (%s) | question=%r",
        intent, user_major, major_kind or "none", question[:80],
    )

    if not use_handbook:
        records = []
        rule_summary = ""
        if structured_only or not suppress_cs_ds:
            # Has a known program — ground on its programs.json requirements.
            context = (
                "(No indexed handbook records exist for this program. Use the "
                "PROGRAM REQUIREMENTS section below as the authoritative source.)"
            )
            sources = (
                build_program_sources(user_major)
                if user_major and intent in _ACADEMIC_INTENTS else []
            )
        else:
            # No major declared — stay neutral, no program to cite.
            context = (
                "(The student has not selected a major, so no major-specific "
                "records are available. Do not assume any particular program.)"
            )
            sources = []
    else:
        # Retrieve wide, then drop the other program's handbook/bulletin before
        # selecting — top_k=16 so the scoped set is still deep enough.
        retrieved_records = filter_records_by_scope(semantic_search(question, top_k=16), major_kind)
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

    # Structured handbook policies — ETM, petitions, substitutions, contacts.
    # Deterministic lookup by (intent, major_kind); no retrieval involved. Only
    # CS/DS have handbooks, so this is empty for every other major.
    #
    # Gated on the same test as the retrieval path above. INTENT_TOPICS maps
    # `general` to advising/graduation topics, so a CS student asking where to
    # eat was handed handbook policy AND cited to the CMPSC handbook PDF. That
    # citation was the most visible symptom: a departmental handbook attached to
    # a dining question. The handbook is authoritative for procedure and silent
    # about everything else.
    policy_snippet = build_policy_snippet(intent, major_kind) if use_handbook else ""
    if policy_snippet:
        for src in policy_sources(major_kind):
            if src["link"] not in {s["link"] for s in sources}:
                sources.append(src)

    resources_snippet = CAMPUS_RESOURCES_SNIPPET if intent == "wellbeing" else ""
    career_snippet = CAREER_RESOURCES_SNIPPET if intent == "career" else ""
    # Real organisations, matched on what ACE has learned about the student and
    # on the question itself. Appended to the career block, whose rules defer to
    # it when present and keep refusing to invent names when it is absent.
    if intent == "career":
        career_snippet += build_clubs_snippet(
            (get_profile(user_id) or {}).get("interests") if user_id else None,
            question=question,
            major=user_major or "",
        )
    profile_snippet = build_profile_snippet(user_id) if user_id else ""
    # Logistics gets the calendar too: "when is my registration window" is a
    # steps question whose answer needs real dates.
    deadline_snippet = (
        _get_deadlines_snippet() if intent in ("deadline", "logistics") else ""
    )
    logistics_snippet = LOGISTICS_SNIPPET if intent == "logistics" else ""
    # Procedures are matched on the QUESTION, not the intent. "I need to
    # retroactively withdraw" routes to `deadline` on the word "withdraw" and
    # would come back with a wall of dates — exactly the wrong answer for
    # someone who has already missed the deadline.
    procedures_snippet = build_procedures_snippet(question)
    # Campus places, matched on the question for the same reason procedures are:
    # "where can I study tonight" has no intent of its own and would otherwise
    # fall through to `general` with nothing behind it.
    places_snippet = build_places_snippet(question)
    money_snippet = build_money_snippet(question)
    events_snippet = build_events_snippet(
        question,
        (get_profile(user_id) or {}).get("interests") if user_id else None,
    )
    recommendation_snippet = (
        _build_recommendation_snippet(user_major, student_doc)
        if intent == "recommendation" and user_major else ""
    )
    aid_snippet = FINANCIAL_AID_RESOURCES_SNIPPET if intent == "financial_aid" else ""
    intl_snippet = INTERNATIONAL_RESOURCES_SNIPPET if intent == "international" else ""

    # How much visual the answer may reach for. Counted from what actually
    # matched — a block never fires on data that isn't there.
    visual_counts = _count_visual_material(
        question, intent, user_major, student_doc, history=history
    )
    visual = decide_visual(question, intent, visual_counts, bool(student_doc))
    visual_directive = build_visual_directive(
        question, intent, visual_counts, bool(student_doc)
    )
    logger.info("visual policy | level=%s block=%s | %s",
                visual["level"], visual["block"], visual["reason"])

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
            message_id = save_exchange(
                user_id, conversation_id, question, deterministic_answer, intent, sources
            )
            yield f"data: {json.dumps({'done': True, 'sources': sources, 'intent': intent, 'used_student_doc': True, 'message_id': message_id})}\n\n"
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
{student_doc_context if student_doc_context else "No student document uploaded."}{profile_snippet}{degree_audit_advisory}{program_snippet if program_snippet else ""}{policy_snippet}{resources_snippet}{career_snippet}{recommendation_snippet}{procedures_snippet}{places_snippet}{money_snippet}{events_snippet}{logistics_snippet}{deadline_snippet}{aid_snippet}{intl_snippet}{gen_ed_snippet}

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
- When a DEPARTMENT HANDBOOK POLICIES block is present, it outranks the advising records for procedure questions (ETM, petitions, substitutions, transfer credit, who to contact). Use its exact numbers and name the step the student has to take.
- Never invent courses, policies, contacts, grades, or substitutions not present in the records.
- If records are insufficient, say so clearly.
- Do not mention internal record numbers.
- If a Degree Audit Advisory is present above, include the recommendation naturally in your answer when it is relevant to what the student asked.
- Keep the tone student-friendly and specific.
{_INTENT_ANSWER_RULES.get(intent, "")}{visual_directive}"""

    try:
        # Build messages: system → history (capped at 6) → current question
        messages_list = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history[-6:]:
                messages_list.append({"role": msg["role"], "content": msg["content"]})

        messages_list.append({"role": "user", "content": question})

        logger.info("ask_advisor_stream | calling model=%r messages=%d", llm.CHAT_MODEL, len(messages_list))

        answer_parts = []
        for delta in llm.chat_stream(messages_list, user_id=user_id):
            answer_parts.append(delta)
            yield f"data: {json.dumps({'text': delta})}\n\n"

        logger.info("ask_advisor_stream | stream complete | sources=%d", len(sources))
        message_id = save_exchange(
            user_id, conversation_id, question, "".join(answer_parts), intent, sources
        )
        # Learn from what the student said, after their answer is already on
        # screen — the extraction call must never sit in front of the response.
        remember(user_id, question)
        yield f"data: {json.dumps({'done': True, 'sources': sources, 'intent': intent, 'used_student_doc': bool(student_doc_context), 'message_id': message_id, 'visual': visual})}\n\n"

    except Exception as e:
        logger.error("ask_advisor_stream | error: %s", e, exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True, 'sources': [], 'intent': intent})}\n\n"