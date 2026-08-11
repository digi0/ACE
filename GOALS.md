# ACE — Goals

> Tactical goal doc for this repo. Strategic, cross-project view is in
> `~/Documents/Projects/hub/goals.md`. If they disagree, the hub doc is intent
> — update this one to match.

**Window:** 2026-05-23 → 2026-08-05 — **CLOSED.** Fall started 2026-08-05; a new window needs setting.
**Priority:** P0
**Phase:** Product ready, cohort not yet in seats
**Last reviewed:** 2026-08-11 — re-baselined against the repo and against production, because the doc had drifted far enough to mislead: six of the nine "Now" items were already done and still listed as pending, and DoD #4 read "Still not built" about something that shipped on 2026-08-02.

> **The one number that matters right now.** Production, 2026-08-11: the
> waitlist holds ten rows but **five real prospects** — the rest are Raghav ×3,
> Sinjini, and a spam signup. **All five have now been sent the code.** Nobody
> has arrived yet: 8 users (mostly ours), 0 new in seven days, last student
> message 2026-08-07, **0 answers rated**, $0.005 spent.
>
> Fall is in its second week. Two bottlenecks, found in that order and only the
> first one fixed: nobody had been invited (they have now), and underneath it,
> **only five real people ever signed up in two months.** The second one is not
> an engineering problem and nothing below will solve it.

---

## The goal

**ACE is the navigation layer for college.** Three rings, inside out:

1. **Courses + degree progress** (shipped) — the wedge. "ChatGPT can't read your degree audit."
2. **College logistics** (now in scope) — how to enroll, how to register, orientation, key dates, deadlines. Students don't just struggle with *what to take*; they struggle with *how the machine works*. Proof point: a brand-new UCSD enrollee (see Track 2) can't easily find dates, enrollment steps, or orientation info.
3. **Career + activities** (roadmap) — clubs, research, internships matched to the student's record and goals. Never described as shipped.

All 749 PSU majors in scope (`programs.json`). Not CS/DS-framed anywhere — copy, brand, or code.

**Interface implication:** the UI must be structured around *navigation moments* (I just enrolled → orientation → registration windows → semester deadlines), not only course tools. A new student's first run should meet them where they are in the college timeline, not drop them into a prereq map.

The product is **live at acecollege.app** behind a waitlist + invite gate. Two tactical tracks this window:

- **Track 1 (PSU):** convert the waitlist into a real first cohort of Penn State students in the first week of fall semester (Aug 5), with a faculty ally amplifying it.
- **Track 2 (UCSD):** get ACE useful for a brand-new UCSD student — starting with logistics navigation — with the founder's brother as design partner and first user.

## Definition of done (was: by August 5) — scored 2026-08-11

1. **Faculty ally activated.** ⬜ **Unknown from here.** Outreach sent, Prof. Faiza Abbas replied, meeting was being scheduled. Whether it happened is yours to record — no artefact in the repo can tell me.
2. **Real students using it.** ❌ **Not reachable from this waitlist, and the bar needs rewriting.** The target says "10+ waitlist signups invited and active". The waitlist has ten rows and **five real prospects** — the other five are Raghav ×3 (`mrmalpani25`, `rlm6084@psu.edu`, `raghav.malpani@outlook`), Sinjini (co-founder), and one spam signup. All five prospects have been sent the access code manually and are stamped `invited_at` (2026-08-11); four are `@psu.edu`, one is a personal address.

   **A perfect result here is five, not ten.** The number cannot come from this list, so either the bar moves or a second source of students does. See "Where the ten are supposed to come from" below.
3. **Doesn't embarrass.** 🟡 **Much better than it was.** Fixed this window: ACE answering questions about New York and writing poetry on request, a prerequisite verdict that said "No" when the answer was yes, a withdrawal procedure sending students to the wrong office, transfer credit misread as 0.75 of 116 credits. Untested by real strangers, which is the only test that counts.
4. **Logs feedback.** ✅ **Done** (2026-08-02). `messages.rating`, `POST /messages/{id}/rating`, thumbs UI, `GET /admin/review`, and `backend/eval/from_transcripts.py` to harvest bad answers into eval items. Caveat: **0 ratings exist**, because no students.

---

## The old "Now → Aug 5" list, scored

Kept rather than deleted, because the pattern is the lesson: eight of nine were
engineering, they all got done, and the one that was not — telling students the
product exists — is the one that decided the outcome.

| # | Item | State |
|---|------|-------|
| 1 | Prof. Abbas meeting | ⬜ yours to record |
| 2 | Feedback rating | ✅ 2026-08-02 |
| 3 | Re-index | ✅ rebuilt; 73 records, content byte-identical to April |
| 4 | Clerk prod keys | ✅ 2026-06-10 (`pk_live` verified decoding to clerk.acecollege.app) |
| 5 | **Invite flow** | ✅ **2026-08-11 — and it was the blocker for DoD #2 the whole time** |
| 6 | Per-user rate limiting | ✅ `CHAT_RATE_LIMIT` / `CHAT_RATE_WINDOW` |
| 7 | RAG health check | ❌ **still not built** — no endpoint exercises retrieval, only `200 OK` |
| 8 | Brand wiring | ✅ 2026-08-11 — emerald across product + landing, Zero Chroma |
| 9 | Provider seam | ✅ `backend/services/llm.py`; only the offline `policy_extractor.py` still imports OpenAI directly, which is the documented exception |

## Now (2026-08-11 →)

Ordered by leverage. The first item is done; the second is the one that decides August, and it is not an engineering problem:

1. ~~**Send the invites.**~~ ✅ **Done 2026-08-11** — all five real prospects were
   sent the shared access code by hand and stamped `invited_at`. Note the
   consequence: the shared code carries no identity, so `redeemed_at` will stay
   empty for this batch and conversion is only visible in aggregate (new `users`
   rows, `user_docs` uploads, `messages`). Per-person attribution starts with the
   next batch, via `POST /admin/waitlist/invite`.

2. **Where the ten are supposed to come from.** This is now the real question and
   it is not an engineering one. A live landing page ran for two months and
   produced **five** real signups — the invite step was blocked, but underneath
   it the supply was thin, and fixing the invite did not fix that. Two readings
   and they need different work: either the waitlist was never the channel and
   Prof. Abbas mentioning ACE to a class always was, or the landing page is
   underperforming and nobody has looked at why. `?ref=` cannot help decide —
   all ten rows say `landing`, so there is no channel breakdown to read. Decide
   which it is before building anything else.
3. **Watch what they ask.** `GET /admin/review?days=7` is the weekly read:
   counts by intent, down-rated answers, ungrounded answers. Then
   `python -m backend.eval.from_transcripts --days 7 --write` turns the failures
   into eval items. This loop is built and has never once run on real traffic.
4. **Decide the August line** (see Open questions — still undecided, and now
   overdue). Is 10 active students the win or the floor?
5. **RAG health check.** The last unbuilt item from the old list.
6. **Track 2 — UCSD Phase A.** Unchanged below, and now the biggest *build*.
   Note the new dependency: the scope gate added 2026-08-11 hardcodes Penn State
   (`ELSEWHERE` in `places_service.py` lists other universities as out of
   bounds, and the prompt says "ACE knows Penn State"). Making ACE multi-school
   means making that gate school-aware — small change, but it is now on the
   critical path and was not when this doc was written.

## Track 2 — UCSD (started 2026-07-22, ASAP)

**Why now:** the founder's brother just enrolled at UCSD and is hitting the exact problem ring 2 describes — can't easily find dates, enrollment steps, orientation info. He is the design partner: his real questions seed the UCSD eval set, and UCSD's new-student window (orientation + fall-quarter enrollment) is happening **right now**, so this can't wait for after Aug 5.

**Sequencing — navigation first, catalog second.** The fast path to useful is NOT scraping 9,000 courses; it's answering "how do I enroll":

### Phase A — logistics wedge (days)
- `school` field on users + index records; UCSD selectable at onboarding
- Scrape UCSD new-student/onboarding, registrar, orientation, and enrollment pages → RAG index tagged `school=ucsd`
- UCSD quarter calendar (registrar) → calendar.json namespaced per school
- Collect the brother's actual questions verbatim → UCSD eval set; iterate until ACE answers them better than the UCSD website does
- First-run experience for "I just enrolled" (navigation moments, per the interface implication above)

### Phase B — catalog (about a week)
- Courses parser: `catalog.ucsd.edu/courses/{DEPT}.html` — static HTML, regular format, prereq strings reuse existing and/or logic
- Curricula parser: `catalog.ucsd.edu/curric/{DEPT}-ug.html` — prose-heavy; quality-gate gaps with "not available yet"
- Quarter plans: `plans.ucsd.edu` (official, per college/year/major; sniff its JSON API)
- Schema: `term_type` (quarter vs semester) + per-college gen-ed (Revelle/Muir/… each have different GE) — the two real modeling differences vs PSU

### Recon facts (verified 2026-07-22)
- UCSD catalog is **static HTML, not CourseLeaf** — new parsers, but unusually scrape-friendly
- Course entries: `CSE 100. Advanced Data Structures (4) … Prerequisites: …` — highly regular
- Suggested plans are NOT in the catalog; they live at plans.ucsd.edu

## Shipped since last review (Jul 22 → Aug 11)

Verified against the repo on 2026-08-11, not recalled.

- **Five new datasets**, each with a service, a trigger vocabulary written in the
  words students type rather than the words institutions index by, and a
  self-check: **clubs 1,303** · **places 178** · **events 166** · **procedures 25**
  · **money 19**. This is ring 2 of the thesis becoming real code.
- **Answer shape.** A verdict/substance/citation contract, and a visual policy
  that rations blocks instead of decorating every reply. Five renderable blocks —
  `map, cards, checklist, strip, plan` — with the rule that a rendered block is
  the *only* channel: the itemised grounding is withheld so the model cannot
  recite the six dining halls it is drawing underneath. The prereq map is
  walkable (`GET /prereq-graph/{code}`); the checklist ticks and persists.
- **Scope.** ACE now knows what it is *not* for. Other cities and institutions,
  general knowledge, writing to order, medical/legal/investment advice — and it
  never mentions its model, cutoff, or training data.
- **Correctness that cost students something.** Transfer credit read properly
  (one real audit went 0.75 → 66.49 credits); the eligibility verdict that said
  "No" when the answer was yes; a withdrawal procedure pointing at the wrong
  office; the unauthenticated `GET /chat` that burned budget with no scope filter,
  deleted.
- **Schema under Alembic** (3 revisions), each guarded so a live database and a
  fresh checkout reach head from different directions with no `stamp` by hand.
- **Brand.** Blue → emerald across product and landing, spent once per view.
- **Eval.** 31 items, grading *both* channels (prose and rendered block).
  Baseline **31/31 hard, judge mean 0.93**. **13 self-check suites.**
- **Invite flow** — see above.

## Shipped in the review before that (Jun 8 → Jul 22)

- **Live on acecollege.app** (www canonical), Vercel Web Analytics on
- **Landing page + waitlist**: `WaitlistEntry` model, `POST /waitlist`, `/access/verify` invite gating, `/admin/waitlist`
- **Cost tracker**: `ApiUsage` per-call metering, `/admin/costs` + estimate endpoint
- **Eval loop**: `backend/eval/` (eval_set.json + run.py) — the "train as we go" mechanism
- **Calendar refresh**: rebuilt Jun 8 + `POST /calendar/refresh` endpoint
- **Message persistence**: chat history to DB with intent + sources
- **Professor outreach**: sent; Prof. Faiza Abbas replied, meeting being scheduled
- **Brand**: advisor-pin logo + 4-poster launch set (not yet wired into app)

---

## Constraints

- **Stay on gpt-4o-mini + text-embedding-3 for the cohort.** The provider-abstraction seam ships this window; the migration does not.
- **Two P0 tracks now.** Track 1 launch-critical items (Abbas meeting, feedback rating, re-index, Clerk prod) and Track 2 Phase A (brother unblocked on UCSD logistics) both hold; everything else queues behind them. If they collide in a given week, the tiebreaker is whichever has the nearer immovable date (PSU fall start vs UCSD enrollment/orientation windows).
- **All 749 majors stay in scope.** Quality-gate major-specific tools — a major with missing data shows an honest "not available yet," never a blank. Do not re-narrow to CMPSC/DTSCE.
- **Known caveats to not trip on:** audit re-upload caveat. **`ADMIN_KEY` IS set on Railway** — this doc previously said it was skipped; verified 2026-08-11 by `/admin/costs` returning 403 rather than 503. Admin endpoints are live and key-gated, but still not hardened for a public audience.

## Open questions

- **Enrollment/registration automation.** Can ACE *do* the enrollment/registration steps for a student (WebReg etc.), not just explain them? Path unknown — credentials, liability, and ToS all unsolved. For now ACE answers "how"; automation is explicitly an open research question, not a commitment.
- **Cohort mechanics.** Invite everyone on the waitlist at once, or batch? What does the invite email say?
- **Success/failure line for August.** Is 10 active students the win bar or the floor? Failure = zero students, or >50% down-rated answers? Define before fall.
- **YC framing.** North star includes YC prep — what artifact does this window need to produce for that (metrics dashboard, demo video, usage graph)? Decide, don't drift.

---

## Notion task DB

- DB URL: https://www.notion.so/3190ae9d0f9b43e7a00882bda6a34d8e
- Data source ID: `2e5d3231-0040-4678-9831-b7120e4dd455`

Notion = individual tasks. This file = intent. Prune Notion against the "Now → Aug 5" list above.

## Out of scope this window

- *Full* OpenAI → owned/OSS model migration (the seam IS in scope; migration is post-fall)
- Fine-tuning a base model (in-window analogue is `backend/eval/`)
- Prescriptive "which major should I declare" recommender (premortem 2026-06-08: ungrounded + high-liability; route to a human advisor)
- Mobile app (web-only; PWA/Capacitor path is the post-fall answer)
- Group / shared sessions
- AI-generated advising notes for advisors (different product)
- Drafting outgoing email to professors/parents on student behalf
- Acting on the student's behalf in university systems (auto-enroll, auto-register) — open question above, not in-window work
- Big public launch (Product Hunt, Twitter) — waitlist + landing page are live, but the megaphone waits until the first cohort proves retention
