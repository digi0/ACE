# ACE — YC Application Prep

Four questions, answered exactly against what's shipped (July 2026), and framed around the real thesis: **ACE is a career-navigation layer for college — not a course chatbot.** Courses are the wedge that works today. Navigating the whole college-to-career path is the company.

---

## 1. Walk me through what a student actually does

They land on **acecollege.app** (the waitlist site). The product runs at **app.acecollege.app**, behind a pilot access gate for now.

The first real session:

1. **Enter an access code** — pilot gate, cached per browser so it's a one-time step.
2. **Sign up** (Google or email).
3. **Pick their major** — one-time, and load-bearing: it scopes every answer and every tool to their degree path. Any of Penn State's 749 majors.
4. **They're in the chat** and can ask immediately — "what am I missing to graduate?", "what's the prereq chain for the course I want next fall?", "when's the spring drop deadline?"

Then the step that makes it *theirs*:

5. **They upload the Degree Audit or What-If report Penn State already gave them** — a PDF they have, no portal login, no credential scraping. ACE parses it (completed courses, grades, GPA, earned credits) and opens a **Dashboard**: credits done, what's remaining, and four tools that now run against *their* record — GPA calculator, Gen-Ed explorer, Prereq map, and a suggested semester plan.

Chat first, upload second, no account-linking required. The upload is the unlock — it's the difference between advice about the catalog and advice about you.

---

## 2. What it does today vs. what we're building

**Live today, for all 749 Penn State majors:**

- **Grounded chat** over Penn State's real advising data — the course catalog, program requirements, handbooks, and bulletin — with intent routing that sends each question (progress, prereqs, substitutions, transfer, gen-ed, deadlines, contacts, aid/visa) to the right sources and behavior. Answers stream live.
- **Personalized audit analysis** — upload → parse → Dashboard with credits, GPA, and remaining requirements for your specific degree.
- **Four tools wired to your uploaded audit** — GPA calculator, Gen-Ed explorer, Prereq map, suggested academic plan. They reshape to whichever major you're in.
- **Self-updating academic calendar** — deadlines derive the current term from today's date; the scraper pulls the current + next academic year automatically.
- **High-liability guardrails** — financial aid and international/visa questions refer out to the right Penn State office instead of advising.

**Building now (the roadmap the wedge is earning):**

- **Automated catalog refresh** — a scheduled re-scrape + diff pipeline so course and program data stays live on its own and flags when Penn State changes a prereq or requirement. In active development.
- **Career-aligned activity navigation** — the expansion. Today ACE knows your courses and your real progress. Next it maps the *rest* of college — clubs, research, internships, involvement, opportunities — to where you want your career to go, personalized to your actual record. This is the difference between "what course do I take" and "what do I *do* with these four years."
- **Study groups / roundtables** — enrollment-gated community, so the students in your exact classes and major can find each other.
- **Feedback + usage instrumentation** — thumbs + query logs, the flywheel that turns real student questions into a better engine.

The line I hold: the career layer is the roadmap, not a shipped claim. The course/audit wedge is real and works today.

---

## 3. Does it actually know the catalog, prerequisites, and degree requirements?

**Yes — and it's structured Penn State data, not the model guessing.** Three layers:

1. **Course catalog** — every Penn State course with code, title, credits, description, and **prerequisites that carry an enforced flag and the actual catalog condition text** (e.g. the literal "at Enrollment: [course]" rule). So when ACE says a course is locked behind a prereq, that's Penn State's own rule, not a hallucination. The prereq-map tool builds its dependency graph straight off this — and it correctly tells apart hard chains ("A *and* B") from alternatives ("A *or* B"), so it never wrongly locks a course you're actually eligible for.

2. **Program requirements** — the requirement structure for all 749 majors. This is what lets a student pick any degree and get a plan and a remaining-requirements read scoped to it.

3. **Advising knowledge** — Penn State handbooks and bulletin content embedded into a retrieval index for the nuanced policy questions that don't live in a requirements table.

**How it got in:** Penn State's catalog and bulletin were scraped into structured JSON; handbooks were chunked and embedded; the retrieval index is pre-built and committed so production never cold-starts.

**How it stays current:** the calendar already self-updates (current + next academic year, term derived from today's date). The course/program catalog is refreshed today by re-running the scraper, and the **automated refresh pipeline is in development** — a scheduled weekly re-scrape with a diff step that surfaces exactly what Penn State changed. When that ships, the whole knowledge base self-heals, not just the calendar.

The depth is the strong part: enforced prereqs, real requirement trees, every major. This is precisely what a general model can't do — it doesn't have Penn State's enforced prereq graph or your degree's requirement structure, so it guesses, and it guesses wrong in the direction that costs a student a semester.

---

## 4. The "oh, damn" moment — and the company behind it

**Shipped today:** a student uploads the degree audit Penn State already handed them and asks *"what do I have left, and what can I actually take next term?"* — and ACE answers about **them**. It reads their completed courses and grades, checks them against their major's requirement tree and Penn State's *enforced* prerequisites, and tells them what's done, what's remaining, and what they're now eligible for. The progress path runs deterministically, without the LLM, so it can't hallucinate a transcript.

Say it plainly: **ChatGPT can't read your degree audit.** Even pasted in, it doesn't know Penn State's enforced prereq chains or your degree's requirement tree — so it'll tell you you're on track when you're missing a requirement, or that a course is open when it's locked. ACE knows the rules *and* it knows you.

**The company behind the moment:** that same engine — your real record meeting the real rules — is what we point at the rest of college. A student doesn't just need the right courses; they need the right research lab, the right club, the right internship, the right involvement to get where they're going. Nobody connects those dots to a career outcome — advisors do courses, career services does resumes, and the student is left stitching it together alone. ACE already holds the two hardest pieces: the student's real academic record and the institution's real structure. Extending that into career-aligned navigation of the *whole* college experience is the "oh, damn" that compounds — the wedge is a course advisor Google can't build, and the company is the thing that walks a student from enrollment to career.
