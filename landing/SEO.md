# SEO for acecollege.app

Written 2026-09-04, at the point where the technical foundation landed and
nothing else had been done. It is a working doc: the audit at the top is
finished, the plan below it is not.

Read `GOALS.md` first if you have not. It says the thing this doc exists to
answer, and says it plainly: *"only five real people ever signed up in two
months. The second one is not an engineering problem and nothing below will
solve it."* Search is one of the few channels that can put ACE in front of a
student who has never heard of it, at the exact moment they need it, without
anyone doing outreach. That is the whole case for this work.

---

## 1. Where we stood, and what changed

The site had no SEO at all. Not "thin", not "needs improvement": the head
carried a title and a viewport tag and nothing else.

| | Before | Now |
|---|---|---|
| `<meta name="description">` | absent | written, 154 chars |
| `<link rel="canonical">` | absent | present on all four pages |
| Open Graph / Twitter card | absent | full set + a purpose-built 1200x630 card |
| `robots.txt` | absent | present, sitemap declared, answer engines allowed |
| `sitemap.xml` | absent | present, four URLs |
| Structured data | absent | Organization + WebSite + WebApplication |
| `<h1>` | **zero on the page** | the hero line, with an accessible name |
| `app.acecollege.app` | indexable | `noindex` + `Disallow: /` |

Two of those were doing active harm rather than just missing an opportunity:

**Every share of the link was a blank rectangle.** No `og:image`, no
`og:title`, no `og:description`. The playbook's second audience is parents,
who "never install anything; they receive a screenshot", and the first
cohort was always going to arrive by a student sending the link to another
student. That link had no preview in iMessage, Slack, Discord or anywhere
else. Of everything in this document, the OG card is the change most likely
to matter this month, and it has nothing to do with Google.

**The gated app was competing with the marketing site.** `app.acecollege.app`
served a sign-in shell on every route with a Vercel SPA rewrite, so a crawler
could index a dozen URLs of the same thin page on a subdomain of the site we
actually want ranked. It is now closed to crawlers from both directions.

### What is still wrong, and cannot be fixed in the head

**One page cannot rank for anything.** acecollege.app is a single scroll
plus three legal pages. There is no page about prerequisites, no page about
the drop deadline, no page about entrance to major. Search engines rank
pages, not products. Everything in section 4 is about fixing this, and until
it is fixed the work above is a foundation with nothing built on it.

**The domain has no authority and no history.** Nothing links to it. This is
the constraint that decides strategy: it rules out competing for the head
terms, and it means the first six months are about accumulating a body of
pages that each answer one narrow question well.

---

## 2. The honest read on what we can win

The instinct is to go after "penn state degree requirements" and similar.
That is unwinnable and it is worth being precise about why.

**psu.edu owns the head terms and always will.** The bulletin is the primary
source, on a .edu with two decades of authority, and Google treats the
institution's own site as canonical for questions about the institution. We
are not going to outrank `bulletins.psu.edu` for "penn state computer science
requirements". Planning as though we might is how six months get wasted.

**The real incumbent is Reddit.** For the questions students actually type,
the results are not psu.edu. They are `r/PennStateUniversity` threads from
2019, a Course Hero page, and a College Confidential thread. Search "can I
retake a class I passed penn state" and see for yourself before writing any
content. This matters because it tells you what the winnable gap looks like:
**psu.edu has the documents, Reddit has the answers, and nobody has both.**
That is the same gap the playbook already identified for the product
("Advisors cover academics. Reddit has breadth with no accountability.
University websites have documents, not answers"), which is a good sign: the
content strategy and the product strategy are the same strategy.

**So the target is the question-shaped long tail.** Individually tiny, in
aggregate the majority of the demand, and specifically the queries where the
answer exists in a PDF that no student is going to read:

| Shape | Example | Who ranks now | Why we can win |
|---|---|---|---|
| Prereq chain | "do i need MATH 230 before CMPSC 465" | Reddit, nothing | We have `courses.json`, resolved |
| Consequence | "what happens if i miss the late drop deadline at penn state" | Reddit, a PDF | The policy is in `policies.json`, in plain words |
| Eligibility | "penn state entrance to major GPA computer science" | a handbook PDF | Same, plus what to do if you miss it |
| Procedure | "how to petition a course substitution penn state" | nothing findable | RAG index has the procedural content |
| Sequencing | "can i still graduate on time if i fail a prereq" | Reddit | This is literally the product's core answer |
| Definitional | "what is a what-if report penn state" | psu.edu, badly | Low volume, trivial to win, good entry point |

None of these are high volume. That is the point: they are cheap to rank
for, they convert far better than a head term because the searcher has the
exact problem ACE solves, and there are thousands of them.

**Timing is a channel, and it applies here too.** The playbook's section 05
notes demand is nocturnal and calendar-spiked: registration week, the days
before a drop deadline, the 48 hours after grades post. Search has a lag of
weeks to months between publishing and ranking, so the deadline content has
to exist *well before* the spike it is written for. Publishing a "late drop
deadline" page during late-drop week is publishing it for next year.

**Answer engines are a first-class channel, not a footnote.** A student
asking an assistant "how do I find out what CMPSC 465 needs first" is exactly
the moment ACE exists for, and the same pages that rank are the pages that get
cited. `robots.txt` allows the AI crawlers explicitly and deliberately; the
comment there explains the trade. Structured, factual, well-sourced pages are
what get quoted, which happens to be the same thing that ranks.

---

## 3. Setup that has to happen once, by a human

None of this is code and none of it can be done from this repo. It is the
gate on measuring anything, so it should happen before section 4 starts.

- [ ] **Google Search Console**, verify `acecollege.app` as a domain property
      (DNS TXT, so it covers the app subdomain too). Submit
      `https://acecollege.app/sitemap.xml`.
- [ ] **Bing Webmaster Tools**, same. Worth the ten minutes: Bing feeds
      ChatGPT search.
- [ ] Confirm **one canonical host**. Pick `acecollege.app` or
      `www.acecollege.app` and 301 the other at the Vercel project level. The
      canonical tags say bare, so the redirect should point that way.
- [ ] Re-check the **OG card** in a real unfurl once deployed. Post the link
      into a Slack DM to yourself, and run it through the LinkedIn Post
      Inspector, which caches aggressively and is the one that punishes a
      mistake for a week.
- [ ] Decide whether **Search Console is wired to anything**. Impressions by
      query is the only number that tells you whether section 4 is working,
      and it is invisible unless someone looks.

---

## 4. The plan: pages, in priority order

Ordered by expected return per unit of work, not by ambition.

### 4.1 An answers section, hand-written, ~15 pages

`/answers/<slug>` covering the highest-intent questions from the table in
section 2. Hand-written, 400 to 800 words, each one answering exactly one
question in the first paragraph and then explaining the mechanism.

Why hand-written and why first: fifteen good pages will teach more about
what ranks than three hundred generated ones, they are the template the
generated pages get built from, and they can ship this month.

Each page needs, to be worth publishing at all:

- The answer in the first two sentences. Not context, not preamble.
- The source named and linked: the handbook page, the bulletin section, the
  office. This is the product's own promise applied to the marketing site,
  and it is what makes the page quotable by an answer engine.
- A visible last-reviewed date, because a policy page with no date is
  worthless to a student and a negative signal to a crawler.
- `FAQPage` or `QAPage` structured data **on the visible text**. The index
  page deliberately carries none for the reason in its head comment; these
  pages can carry it honestly.
- The Penn State disclaimer. Every one of these pages is a page about a
  university we are not affiliated with, and the footer disclaimer that
  covers the landing page has to cover these too.

### 4.2 Programmatic program pages, ~749 of them

This is the asset nobody else has. `programs.json` and `courses.json` are
already structured, already ours, and already power the product. A page per
program at `/programs/<slug>` is the single largest addressable surface here.

**It is also the way this goes badly wrong, so read this part twice.** 749
pages that restate the bulletin are a duplicate of psu.edu with less
authority, which is at best ignored and at worst a manual action for scaled
content abuse. Google's spam policy is explicit about pages generated at
scale that add nothing. The bar to clear is not "is it accurate", it is
**"does this page contain something the bulletin does not"**, and the honest
answer for a straight dump of `programs.json` is no.

What clears the bar, all of which we can derive and the bulletin does not
publish:

- **The prerequisite chain resolved.** The bulletin lists requirements; it
  does not tell you that CMPSC 465 sits behind MATH 230 sits behind MATH 141,
  which is three semesters. `program_service.py` already computes this.
- **The real sequence**, from the suggested plan, semester by semester,
  including where the plan is tight and a single failure costs a year.
- **Alternatives stated as alternatives.** The recommendation bracket already
  carries this invariant (MATH 110 *or* 140 must never read as a conjunction).
  It is also the single most common way students misread the bulletin.
- **Gen-ed overlap**, which courses double-count. Students hunt for this and
  the bulletin makes them derive it.
- **What changed from last catalog year**, once we have two years of data.

If a program has too little data to produce that, **the page should not
exist.** A thin page that exists is worse than a page that does not. Expect
to publish meaningfully fewer than 749.

Sequencing: build the template, publish 20, wait six weeks, read Search
Console. If those 20 get impressions, scale. If they do not, the template is
wrong and 749 of it is 749 times wrong.

### 4.3 Course pages, ~9,439 of them

Same asset, same trap, much larger. `/courses/CMPSC-465` answering "what do I
need before this, what does it unlock, when is it offered".

Do not start this until 4.2 has been measured. The failure mode is identical
and the blast radius is thirteen times bigger.

### 4.4 The calendar pages

Deadline content, published against the academic calendar we already scrape
(`calendar_scraper.py`). Highest-intent queries in the entire set, and the
strictest timing: live at least eight weeks before the date, or it ranks the
week after everyone needed it.

---

## 5. Things not to do

- **Do not buy links, and do not pay for a "student blog network" placement.**
  A new domain with a spike of paid links is the easiest pattern in the world
  to detect.
- **Do not write for a keyword instead of a student.** Every page above is
  answerable in one paragraph. If the draft has a 300-word introduction
  before the answer, the draft is wrong.
- **Do not generate the programmatic pages until a hand-written template has
  been proven.** See 4.2.
- **Do not put marketing copy on `app.acecollege.app` hoping it ranks.** It
  is `noindex` on purpose. Content goes on the marketing site.
- **Do not claim, imply, or let structured data suggest a Penn State
  affiliation.** The footer disclaimer is not decoration. It is also a
  trademark question, not only an SEO one.
- **Do not chase rank positions.** Impressions and clicks by query in Search
  Console are the measurement. Rank for a long-tail query is noise.

---

## 6. Where the files are

| Thing | Path |
|---|---|
| Head, structured data, h1 | `landing/index.html` |
| Crawl rules | `landing/public/robots.txt` |
| Sitemap (hand-maintained, see its comment) | `landing/public/sitemap.xml` |
| OG card, and the script that builds it | `landing/public/og.png`, `scripts/build-og-image.js` |
| App exclusion | `frontend/index.html`, `frontend/public/robots.txt` |
| Program + course data for section 4 | `backend/data/programs.json`, `courses.json` |
| Policy data for section 4.1 | `backend/data/policies.json` |
| Calendar data for section 4.4 | `backend/services/calendar_scraper.py` |
