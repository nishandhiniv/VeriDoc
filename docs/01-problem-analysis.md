# Phase 1 – Understand the Problem
**Project:** MH26-01 · Smart Admission Document Validation
**Event:** Maatram HackForge 2026–27 · Track: Software · Theme: Maatram Community
**Status:** ✅ APPROVED

---

## 1. The problem statement (summary)
Applicants to the admission process:
1. upload a **profile photograph**,
2. upload their **academic mark sheet(s)**,
3. **type their marks** into the admission form.

Today staff check all of this **by hand**. That is slow, and mismatched marks or poor-quality photos are easy to miss.

We must build an **automated validation solution** that:
- extracts marks from the uploaded mark sheet and compares them with the typed marks, subject by subject
- flags discrepancies and missing or inconsistent information
- shows an **Entered vs. Uploaded** comparison for each field
- produces an **exception report** for cases that need manual review
- validates the photo with **measurable checks**: resolution, width × height, aspect ratio, file size, format, orientation, min/max dimensions, brightness and basic quality

**Hard constraint:** the core validation **must not use Generative AI or LLMs**. Allowed: Python, OCR (Tesseract / PaddleOCR), OpenCV, Pillow, rule engines, and statistical or deterministic checks.
**Data constraint:** use **synthetic** mark sheets only. Never use real students' documents.

**Expected deliverables (from the catalogue):**
- a working prototype that produces a validation report for each application
- a manual-review queue for exceptions
- accuracy results on a sample set of mark sheets and photos

---

## 2. The actual problem
The core issue is **not** "there is no upload form". It is:

> Reviewers cannot quickly and reliably tell whether what an applicant **typed** matches what the applicant **uploaded**, or whether the photo is usable. Errors slip through, or reviewers spend most of their time on applications that were fine all along.

So the real value is **triage**:
- applications that pass every check move forward with minimal effort
- applications with problems are flagged, with the **exact field** and the **exact reason**, so a human can decide fast

---

## 3. Why it needs a solution
| Without automation | Consequence |
|---|---|
| Every mark is checked by eye | Slow. Reviewer time grows with every applicant. |
| Typos or inflated entered marks get missed | Wrong eligibility or merit decisions. Unfair to honest applicants. |
| Bad photos are found late | Applicants have to be contacted again, which adds delay. |
| No record of what was checked | Decisions are hard to audit or explain. |

> ⚠️ We have **no verified numbers** on how many applications Maatram receives or how long a manual check takes. We will **not** invent them. If you can get real figures from Maatram, we'll use them. Otherwise they stay marked as *assumptions*.

---

## 4. Target users
| User | Role in the system | Main goal |
|---|---|---|
| **Applicant (student)** | Fills in the form, types marks, uploads the mark sheet and photo | Submit once, correctly, and know immediately if something is wrong |
| **Reviewer (admission staff / volunteer)** | Works through the exception queue and makes final decisions | Spend time only on real problems, and see exactly what is wrong |
| **Admin (programme coordinator)** | Sets the rules: subjects, photo limits, tolerance | Change rules without changing code |

*Primary user for judging: the **Reviewer**, because the problem statement is about staff effort.*

---

## 5. Needs, difficulties and expectations
**Applicant**
- Needs: a simple form, clear upload instructions, and instant feedback on photo problems
- Difficulties: low-end phones, poor scans, unsure which photo size is accepted
- Expects: to be told *what* is wrong and *how* to fix it ("Photo is 180×220; minimum is 300×400")

**Reviewer**
- Needs: a list of applications sorted by status (Pass / Needs review / Fail), with a side-by-side Entered vs. Uploaded view
- Difficulties: many applications, mark sheets in different layouts, unclear scans
- Expects: never to be told "Match" when the system was not sure. Low-confidence OCR must go to review, not pass silently.

**Admin**
- Needs: to configure the subject list, photo rules and tolerance
- Expects: a summary of how accurate the system is

---

## 6. Proposed solution
A **web application** with three parts:

```
Applicant ──► Application form + uploads
                    │
                    ▼
          Validation engine (Python, no LLM)
          ├─ Mark sheet: preprocess (OpenCV) → OCR (Tesseract/PaddleOCR)
          │              → parse subject/mark pairs (rules + regex + fuzzy subject match)
          │              → compare with entered marks → Match / Mismatch / Missing / Low-confidence
          └─ Photo:      Pillow/OpenCV measurements → rule checks → Pass / Fail per rule
                    │
                    ▼
          Validation report (stored in database)
                    │
                    ▼
Reviewer ──► Dashboard + manual-review queue → Approve / Reject / Request re-upload
Admin    ──► Rule settings + accuracy report on synthetic test set
```

Key design principles:
1. **Deterministic and explainable.** Every result says which rule produced it.
2. **Fail safe.** When OCR confidence is low or a subject isn't found, the field becomes **"Needs review"**, never a false "Match".
3. **Measurable.** A built-in evaluation runs the engine over a labelled synthetic dataset and reports accuracy.

---

## 7. Project overview
| Item | Description |
|---|---|
| Product name | *To be decided by team* (working name: **VeriDoc**) |
| One-liner | Automatically checks admission mark sheets and photos against what applicants typed, and sends only the real problems to a human reviewer |
| Type | Full-stack web application (frontend + backend API + database + OCR/image-processing engine) |
| Core output | Per-application validation report + manual-review queue + accuracy report |

---

## 8. Project scope (draft)
**In scope**
- Applicant form: personal details, typed subject marks, mark sheet upload, photo upload
- Mark sheet OCR and extraction for a **fixed, small set of synthetic mark sheet templates**
- Subject-level comparison: Match / Mismatch / Missing / Low-confidence
- Photo validation: format, file size, resolution, min/max dimensions, aspect ratio, orientation, brightness, blur
- Validation report (the table format from the catalogue example)
- Reviewer dashboard and manual-review queue with decision + comment
- Synthetic dataset generator + accuracy evaluation
- Deployment to a public URL

**Out of scope (planned)**
- Any GenAI/LLM in validation (forbidden by the problem statement)
- Real student data
- Face recognition / identity verification
- Handwritten mark sheets
- Verifying authenticity with exam boards (anti-forgery)
- Payments, SMS/email notifications, multi-language UI *(could be future work)*

---

## 9. Assumptions, limitations and risks
**Assumptions (to be confirmed)**
- A1. Mark sheets are **printed/typed**, not handwritten.
- A2. ✅ **Confirmed by team:** support **Tamil Nadu State Board (SSLC, HSC +2)** and **CBSE (Class 10, Class 12)**, which is 4 layouts in total. We build **synthetic** templates that follow the general structure of each (subject rows, marks columns, total) but contain no real data, logos or seals. Unknown layouts → manual review.
- A2a. Each layout gets its own **template profile** (subject list + parsing rules), so adding a board later means adding config, not rewriting code.
- A3. Uploads are images (JPG/PNG) and possibly PDF.
- A4. A mark "matches" only if the extracted value equals the entered value exactly. No tolerance by default.
- A5. Photo rules (e.g. min 300×400, aspect ratio range, max size) are configurable. Starting values come from the catalogue example.

**Limitations**
- OCR accuracy drops on blurry, skewed, or low-light phone photos.
- Unknown mark sheet layouts will mostly go to manual review rather than being parsed.
- "Photo quality" covers measurable properties only. It cannot judge whether the person in the photo is the applicant.

**Risks**
| Risk | Impact | Mitigation |
|---|---|---|
| OCR misreads digits (e.g. 8 ↔ 3, 0 ↔ O) | False mismatches | Preprocessing, digit-only OCR on mark fields, confidence threshold → review queue |
| Tesseract/PaddleOCR is hard to install on free hosting | Deployment fails | Use Docker; choose a host that supports it; test deployment early |
| Too many features for the time available | Unfinished demo | At most 3 Must-Haves; cut aggressively |
| Accuracy numbers look made up | Loss of credibility | Measure only on our labelled synthetic set and publish the method |

---

## 10. Time budget (confirmed by team)
- **4 days × 1–2 hours/day ≈ 4–8 hours of team time.** No hard deadline. Quality over speed.
- Claude drafts the documents, designs and code. Team time goes to **reviewing, approving, running and testing**, so it has to be spent on decisions, not typing.

| Day | Phases | Team does (≈1–2 h) |
|---|---|---|
| 1 | Phase 1–3: problem, requirements, backlog | Answer questions, review and approve the backlog |
| 2 | Phase 4–5 + start Phase 6: design, setup, validation engine (photo + first mark sheet template) | Approve the design, run the project locally once |
| 3 | Phase 6: form, reviewer queue, report, database, second template | Test each story as it lands |
| 4 | Phase 7–9: QA, accuracy evaluation, deployment, presentation | Run the QA checklist, check the live site, rehearse the demo |

**Scope consequence:** all 4 templates stay in plan, but only **TN HSC + CBSE XII** are guaranteed (Must). **TN SSLC + CBSE X** are similar layouts that should be cheap once the template-profile system works (Should). Anything slipping beyond Day 4 is cut, not rushed.

## 11. Team (confirmed)
4 members: **BA, UI/UX, Developer, QA**. Python and web experience is limited, and the team uses Claude Code for development.
→ The stack must use **one main language**, few moving parts, and code that beginners can read and explain to judges.

**Recommended stack (proposed; finalised in Phase 5):** Python · Flask · Jinja2 server-rendered pages · plain CSS + minimal vanilla JS · SQLite via SQLAlchemy · Flask-Login · Tesseract (pytesseract) + OpenCV + Pillow · pytest + Playwright · Docker for deployment.
Rejected for now: React (second language and build tooling), PaddleOCR (heavy to install and deploy), Streamlit (not a real multi-page website with auth).

## 12. What "done" means (confirmed: no rubric available)
The plan is built around the catalogue's **three expected deliverables**. Quality, functionality, accuracy and UI/UX are the stated priorities.

| # | Deliverable | Becomes (proposed for Phase 3) |
|---|---|---|
| D1 | Validation report for each application | Must-Have 1: **Automated validation + report** (marks + photo, Entered vs. Uploaded) |
| D2 | Manual-review queue for exceptions | Must-Have 2: **Reviewer queue + decision** (approve / reject / request re-upload) |
| D3 | Accuracy results on sample mark sheets and photos | Must-Have 3: **Labelled synthetic dataset + accuracy report** (measured, never estimated) |

Each deliverable maps to exactly one Must-Have, which fits the "at most 3 Must-Haves" rule. Everything else (applicant live photo feedback, admin rule settings, extra templates, styling polish) is ranked Should/Could in Phase 3.

## 13. Hosting (confirmed)
**Render, free Docker plan**, deployed from a GitHub repository.
- Docker image includes Tesseract, so OCR runs the same locally and online.
- The free plan sleeps when idle, so the first request after a pause is slow. Mitigation: open the site a few minutes before the demo, and record a **backup demo video**.
- The free plan's disk does not persist across restarts or redeploys, so **SQLite data and uploaded files reset**. Mitigation: the app **seeds demo applications and the synthetic dataset on startup**, so the demo always has data. This is acceptable for a prototype and is listed as a limitation; production would use a managed database and file storage.

## 14. Decisions log
| # | Question | Answer |
|---|---|---|
| Q1 | Mark sheet formats | TN State Board (SSLC, HSC) + CBSE (X, XII); TN HSC + CBSE XII guaranteed |
| Q2 | Time | ~4 days × 1–2 h/day, no hard deadline, quality over speed |
| Q3 | Team | 4 members (BA, UI/UX, Dev, QA), beginners → Python + Flask stack |
| Q4 | Judging | No rubric → plan around the 3 catalogue deliverables |
| Q5 | Hosting | Render (free, Docker) |

## 15. What can realistically be built
Realistic for a hackathon team:
- ✅ Full flow for **2 guaranteed synthetic templates** (TN HSC, CBSE XII), plus **2 Should templates** (TN SSLC, CBSE X) added in priority order if time allows (matches §10)
- ⚠️ CBSE mark sheets usually split marks into theory + practical/internal and show grades. The parser must take the **total per subject**, and the entered-marks form must ask for that same value.
- ✅ All photo checks listed in the problem statement (all deterministic, so low risk)
- ✅ Report + review queue + accuracy evaluation
- ⚠️ Generic support for "any mark sheet layout": **not realistic**. Unknown layouts go to manual review.

---

## Critical review of this phase
- **Missing information:** resolved, see §14. Still unknown: real Maatram volumes and exact photo rules. Defaults are taken from the catalogue example (min 300×400) and stay configurable.
- **Biggest technical risk:** OCR parsing of mark sheets. It should be prototyped first in Phase 6.
- **Possible improvement:** give applicants live photo feedback *before* they submit. That could cut re-uploads. It's a candidate for Should-Have in Phase 3.
