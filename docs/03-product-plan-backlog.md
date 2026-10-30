# Phase 3 – Product Plan & Backlog
**Project:** MH26-01 · Smart Admission Document Validation (working name: VeriDoc)
**Based on:** `01-problem-analysis.md` (approved) · `02-requirements.md` Revision 2 (approved)
**Status:** DRAFT – waiting for team approval. **No code is written until this backlog is approved.**

---

## 1. Planning principles (from your instructions)
1. **One working end-to-end flow first**, then widen. A thin slice that runs from submit → report → queue → decision → accuracy beats many half-built screens.
2. **Fail-safe is non-negotiable.** Uncertain OCR, unknown layout or any processing error → **Needs review**. A planted mismatch reported as "Match" is a release-blocking bug.
3. **Accuracy is measured, never estimated.**
4. **Essential vs. optional is explicit.** Essential = the 13 core stories below. Optional = enhancement backlog, built only after every core story passes.
5. **Timeline is 4–8 hours of team time.** Claude writes code; the team reviews, runs and tests. If we fall behind, we cut from the optional list, never from the fail-safe or accuracy work.

---

## 2. Feature prioritisation (MoSCoW)

### Must Have: exactly 3 features (one per deliverable)
| # | Feature | Deliverable | What "working" means |
|---|---|---|---|
| **MH-1** | **Automated validation + report** | D1 | Applicant submits → engine checks marks (TN HSC, CBSE XII) and photo → stored report in the catalogue table format |
| **MH-2** | **Manual-review queue + decisions** | D2 | Reviewer logs in → sees Needs-review cases → opens report → approves / rejects / requests re-upload with audit trail |
| **MH-3** | **Synthetic dataset + measured accuracy report** | D3 | 40 mark sheets + 30 photos with ground truth → evaluation → metrics page (clean vs. degraded) |

### Should Have: optional enhancements, built in this order if time allows
| Order | ID | Enhancement | Req IDs | Why this order |
|---|---|---|---|---|
| 1 | O-1 | Instant photo pre-check on the form (warn only) | FR-A07 | Biggest applicant UX gain; reuses US-04 code |
| 2 | O-2 | Dashboard with status counts | FR-Q06 | Strong demo visual; small |
| 3 | O-3 | Settings page for 🔧 values | FR-S03 | Admin persona; values already stored in DB |
| 4 | O-4 | Queue search + board filter | FR-Q08 | Small |
| 5 | O-5 | Applicant status lookup | FR-A08 | Small |
| 6 | O-6 | Templates TN SSLC + CBSE X | FR-V05 | Config work once US-05/07 done |
| 7 | O-7 | Identity check: register number + name | FR-V09 | Needs extra parsing |
| 8 | O-8 | Contrast check, print-friendly report, spot-check override, CSV/MD export | FR-P09, R06, Q05, E07 | Small polish items |
| 9 | O-9 | PDF upload + de-skew | FR-A12, FR-V12 | Least demo value; we control skew in synthetic data |

### Could Have (only if everything above is done)
FR-A09 re-upload flow · FR-V10 total check · FR-P10 face detection · FR-Q07 queue CSV export · FR-S05 template editor UI

### Won't Have (this version)
GenAI/LLM in validation · real student data · applicant accounts · face recognition / identity verification · handwritten sheets · other boards · authenticity / DigiLocker · notifications, payments, multi-language, mobile app. *(Unchanged from Phase 2 §11.)*

---

## 3. Smallest practical working scope
**Definition:** the minimum system that honestly demonstrates **D1, D2 and D3 end-to-end on the deployed site**, without weakening accuracy or the fail-safe rule.

```
 Applicant                     Engine (no GenAI)                    Reviewer / Admin
 ─────────                     ─────────────────                    ────────────────
 Home (rules) ─► Form ─► Upload ─► Review ─► Submit
                                              │
                                              ▼
                               Photo checks P01–P08 ──┐
                               OCR + parse (HSC, XII) ├─► Report (stored) ─► Queue ─► Decision + audit
                               Compare + fail-safe ───┘                          ▲
                                                                                 │ login + roles
 Dataset generator (40 + 30) ─► Evaluation ─► Accuracy page (clean vs degraded) ─┘
```

**Included (essential):** everything in the diagram = 13 core stories, covering all **43 Must** functional requirements.

**Deliberately excluded from the essential scope** (all in §2 Should/Could): live photo pre-check, dashboard, settings UI, search/board filter, status lookup, extra templates, identity check, PDF, de-skew.
→ None of these is needed to *demonstrate* D1–D3, and none affects validation accuracy or the fail-safe rule.

**Essential, not optional, even though it adds work:**
- **Both guaranteed templates (TN HSC + CBSE XII)**: confirmed in Phase 1. CBSE XII is built **after** the end-to-end flow works on TN HSC. If it is at risk at the start of Day 4, we raise it with the team rather than cutting it silently.
- **Degraded dataset variants**: without them, accuracy figures would be misleadingly high.
- **Fail-safe tests**: they protect the most important promise of the system.

---

## 4. Success metrics (measurable)
| ID | Metric | Target | How measured | Type |
|---|---|---|---|---|
| SM-1 | End-to-end flow works on the deployed site: submit → report → queue → decision | Pass | Playwright test + manual check (Phase 7/8) | **Release gate** |
| SM-2 | **False "Match" count** on planted mismatches (all 40 sheets) | **0** | Evaluation run (US-12) | **Release gate** |
| SM-3 | Low-confidence / unknown-layout cases routed to Needs review | **100 %** | Unit tests (US-06) + evaluation | **Release gate** |
| SM-4 | Mark extraction accuracy, **clean** sheets (field level) | ≥ 95 % | Evaluation run | Target (reported as measured) |
| SM-5 | Mark extraction accuracy, **degraded** sheets | No target; reported honestly | Evaluation run | Reported |
| SM-6 | Mismatch detection recall / precision on planted errors | Recall 100 % (anything missed must be "Unreadable"/review, not "Match"); precision reported | Evaluation run | Target |
| SM-7 | Photo rule results agree with labels (30 photos) | 100 % (rules are deterministic) | Evaluation run | Target |
| SM-8 | % of *correct* synthetic applications sent to review (false alarms) | No target; reported (shows how much reviewer work is saved) | Evaluation run | Reported |
| SM-9 | Validation time per application on Render | ≤ 20 s | Timed in Phase 5 (early) and Phase 7 | Target (NFR-01) |
| SM-10 | Core stories passing all acceptance criteria | 13 / 13 | QA checklist (Phase 7) | **Release gate** |
| SM-11 | A stranger runs the app from README | ≤ 5 min | Team member follows README on a clean machine | Target (NFR-12) |

---

## 5. Epics
| Epic | Name | Goal | Deliverable | Stories |
|---|---|---|---|---|
| **EP-1** | Application intake | Applicant submits details, marks and files and gets a reference number | D1 | US-01, US-02, US-03 |
| **EP-2** | Validation engine | Deterministic, fail-safe checks of photo and marks | D1 | US-04, US-05, US-06, US-07 |
| **EP-3** | Report & review | Reviewer sees reports and decides on exceptions | D1, D2 | US-08, US-09, US-10 |
| **EP-4** | Accuracy evaluation | Measured accuracy on labelled synthetic data | D3 | US-11, US-12 |
| **EP-5** | Platform & demo readiness | Seed data, error handling, deployable | D1–D3 | US-13 |

---

## 6. User stories (13 core stories)
**Format:** *As a … I want … so that …* · **Acceptance criteria (AC)** in Given / When / Then · **Size:** S (≤ 30 min team review/test), M (30–60 min), L (> 60 min).
All 🔧 values come from the settings table (Phase 2 §5); tests use those defaults.

---

### EP-1 · Application intake

#### US-01 · Enter details and marks
*As an **applicant**, I want to enter my details, choose my board and type my subject marks, so that my application can be checked against my mark sheet.*
**Req:** FR-A01, FR-A02, FR-A03, FR-A04 (input part) · NFR-08, NFR-09, NFR-10 · **Size:** M · **Depends on:** — (templates config from US-05/07)

| AC | Given / When / Then |
|---|---|
| AC1 | Given I am on the site without an account, when I click **Start application**, then the form opens (no login asked). |
| AC2 | When I choose "TN HSC" or "CBSE XII", then only that template's subjects are offered, and I can add between the template's min and max number of subjects. |
| AC3 | When I leave a required field empty (name, DOB, contact, board, register number, a mark), then I cannot continue and a plain-language message appears next to that field. |
| AC4 | When I type a mark that is not a whole number, or is below 0 or above the subject maximum, then I see "Enter a whole number from 0 to {max}". |
| AC5 | When I choose the same subject twice, then I see "Each subject can only be entered once". |
| AC6 | Every input has a visible label and can be reached with the keyboard; the form is usable at 360 px width. |

#### US-02 · Upload files, review and submit
*As an **applicant**, I want to upload my mark sheet and photo, check everything once more and submit, so that I get a reference number.*
**Req:** FR-A04 (file part), FR-A05, FR-A06, FR-A10 · NFR-06, NFR-07 · **Size:** M · **Depends on:** US-01, US-13 (DB)

| AC | Given / When / Then |
|---|---|
| AC1 | When I upload a mark sheet (JPG/PNG) and a photo (any image), then both are accepted, even if the photo breaks a photo rule (rules are reported later, never blocked here). |
| AC2 | When I upload a file that is not an image (e.g. a `.txt` renamed to `.jpg`), then it is rejected with "This file isn't an image. Upload a JPG or PNG." (detected by content). |
| AC3 | When I upload a file over the 10 MB hard cap 🔧, then it is rejected with a message stating the limit. |
| AC4 | When I reach the **review screen**, then I see all my details, subjects with marks, and file names with thumbnails, each section with an **Edit** link that returns me to it with my data kept. |
| AC5 | When I click **Submit**, then validation runs and I see a confirmation page with a unique reference number in the format `VD-YYYY-NNNNN`. |
| AC6 | Uploaded files are stored with random server-side names; the form shows "Prototype – do not upload real documents". |

#### US-03 · Home page with live photo rules
*As an **applicant**, I want to see what documents and photo rules are required before I start, so that I prepare the right files.*
**Req:** FR-A11 · NFR-08 · **Size:** S · **Depends on:** US-13 (settings stored)

| AC | Given / When / Then |
|---|---|
| AC1 | When I open the home page, then I see the documents needed and the photo rules (format, size, min/max dimensions, aspect ratio, orientation). |
| AC2 | Given a 🔧 photo setting is changed in the database, when I reload the home page, then the new value is shown (rules are read from settings, never typed into the page). |

---

### EP-2 · Validation engine (no GenAI/LLM)

#### US-04 · Photo validation
*As a **reviewer**, I want each photo checked against measurable rules, so that I don't have to judge photo quality by eye.*
**Req:** FR-P01–FR-P08 · NFR-03, NFR-04, NFR-05 · **Size:** M · **Depends on:** — (first engine story; built test-first)

| AC | Given / When / Then |
|---|---|
| AC1 | For every photo, the engine returns **8 results** (format, file size, min resolution, max dimensions, aspect ratio, orientation, brightness, sharpness), each with Pass/Fail, the **measured value** and the **rule**. Example: "Fail · 180 × 220 · minimum 300 × 400". |
| AC2 | A 180 × 220 JPEG fails min resolution; a 600 × 800 JPEG passes. |
| AC3 | A landscape image fails orientation; a portrait image stored sideways with EXIF rotation is judged **after** applying EXIF. |
| AC4 | A very dark image (mean < 70 🔧) fails brightness; a heavily blurred image (Laplacian variance < 60 🔧) fails sharpness. |
| AC5 | A GIF/BMP/WebP image fails the format check (only JPEG/PNG 🔧 pass). |
| AC6 | If the photo cannot be read at all, the result is **"Processing error → Needs review"**, never a crash and never a Pass. |
| AC7 | Thresholds are read from settings; changing a setting changes the outcome without code changes (unit-tested). |

#### US-05 · Read the TN HSC mark sheet (OCR + parsing)
*As a **reviewer**, I want the system to read subject marks from a TN HSC mark sheet, so that they can be compared with what was typed.*
**Req:** FR-V01, FR-V02, FR-V03, FR-V04 (TN HSC) · NFR-04, NFR-05 · **Size:** L · **Depends on:** US-11 (sample sheets, at least a first few) · **Highest technical risk, so built first in Phase 6.**

| AC | Given / When / Then |
|---|---|
| AC1 | Given a clean synthetic TN HSC sheet, when it is processed, then the engine returns every subject on the sheet with its **total mark** and an OCR **confidence** (0–100). |
| AC2 | Subject names are matched to the template using aliases and fuzzy matching (e.g. "MATHS" → "Mathematics"). |
| AC3 | Pre-processing (grayscale, denoise, threshold) is applied before OCR; mark fields are read digit-only. |
| AC4 | The template (subject list, aliases, max marks, parsing hints) lives in a config file, not in code. |
| AC5 | On the first 5 clean TN HSC sample sheets, every extracted mark equals the ground truth. *(Early quality check; full measurement is US-12.)* |

#### US-06 · Compare marks and apply the fail-safe rule
*As a **reviewer**, I want each entered mark compared with the uploaded sheet, with anything uncertain sent to me, so that no wrong application is auto-cleared.*
**Req:** FR-V06, FR-V07, FR-V08, FR-V11, FR-R01 · NFR-02, NFR-03 · **Size:** M · **Depends on:** US-05 · **Built test-first; these tests are release gates (SM-2, SM-3).**

| AC | Given / When / Then |
|---|---|
| AC1 | Entered 92, sheet 92 (confidence ≥ 70 🔧) → **Match**. |
| AC2 | Entered 85, sheet 88 → **Mismatch**, showing "Entered: 85, Uploaded: 88". |
| AC3 | Subject entered but not found on sheet → **Missing on sheet**. |
| AC4 | Subject on sheet but not entered → **Not entered**. |
| AC5 | **Fail-safe:** OCR confidence < 70 🔧 for a subject → **Unreadable (low OCR confidence)**, **even if the digits happen to equal the entered mark**. |
| AC6 | **Fail-safe:** layout not recognised or fewer subjects parsed than the template minimum → whole mark-sheet section **Needs review**. |
| AC7 | **Fail-safe:** any exception in the engine → **Needs review** with a "Processing error" row; never Auto-cleared. |
| AC8 | Completeness = Pass only when every entered subject is found and none are left over. |
| AC9 | Overall status = **Auto-cleared** only if *every* mark row is Match, completeness passes and *every* photo check passes; otherwise **Needs review**. There is no automatic Reject. |

#### US-07 · Read the CBSE XII mark sheet
*As a **reviewer**, I want CBSE XII mark sheets read correctly, including the theory/practical split, so that CBSE applicants are checked too.*
**Req:** FR-V03, FR-V04 (CBSE XII) · **Size:** M · **Depends on:** US-05, US-06 (reuses both; mainly a new template file + tests) · **Built after the end-to-end flow works on TN HSC.**

| AC | Given / When / Then |
|---|---|
| AC1 | Given a clean synthetic CBSE XII sheet with theory, practical and total columns, then the engine extracts the **total** column per subject, not theory or practical. |
| AC2 | A test proves that when theory ≠ total, the total is used (CBSE trap from Phase 2). |
| AC3 | On the first 5 clean CBSE XII sample sheets, every extracted mark equals the ground truth. |
| AC4 | All US-06 fail-safe ACs also pass for CBSE XII sheets. |

---

### EP-3 · Report & review

#### US-08 · Validation report page
*As a **reviewer**, I want one page that shows every check with Entered vs. Uploaded values next to the documents, so that I can see exactly what is wrong.*
**Req:** FR-R01, FR-R02, FR-R03, FR-R04, FR-R05, FR-R07 · NFR-04, NFR-09 · **Size:** M · **Depends on:** US-02, US-04, US-06, US-09

| AC | Given / When / Then |
|---|---|
| AC1 | The report shows the overall status and a table **Validation · Result · Details** in the catalogue format, e.g. "Mathematics Marks · ❌ Mismatch · Entered: 85, Uploaded: 88". |
| AC2 | Every row shows the rule/reason; mark rows also show OCR confidence. |
| AC3 | The uploaded mark sheet and photo are shown beside the table (stacked on narrow screens). |
| AC4 | Each result has **icon + text + colour** (✅ Match / ❌ Mismatch / ⚠️ Unreadable…); meaning is clear in greyscale. |
| AC5 | Reopening a report does not re-run OCR (results are read from the database; verified by timing/log). |
| AC6 | Opening a report without being logged in redirects to login. |

#### US-09 · Reviewer and admin login with roles
*As a **reviewer or admin**, I want to log in with my own account, so that only authorised people see applications and settings.*
**Req:** FR-S01, FR-S02 · NFR-06 · **Size:** S · **Depends on:** US-13 (seeded accounts)

| AC | Given / When / Then |
|---|---|
| AC1 | With a correct email + password I am logged in; with a wrong one I see "Email or password is incorrect" (no hint which one). |
| AC2 | Passwords are stored hashed (never plain text in the database). |
| AC3 | A **Reviewer** can open queue and reports but gets **403** on Accuracy pages; an **Admin** can open everything. Checked on the server, not just hidden links. |
| AC4 | All forms (login, decisions) are CSRF-protected; a request without a valid token is rejected. |
| AC5 | Logout ends the session; the back button doesn't show protected pages again. |

#### US-10 · Review queue and decisions
*As a **reviewer**, I want a queue of applications needing review where I can record a decision, so that every exception is handled and traceable.*
**Req:** FR-Q01, FR-Q02, FR-Q03, FR-Q04 · **Size:** M · **Depends on:** US-08, US-09

| AC | Given / When / Then |
|---|---|
| AC1 | The queue lists reference, name, board, submitted time, overall status and **number of issues**. |
| AC2 | The default view shows **Needs review** only, oldest first; a status filter switches to Auto-cleared or Decided. |
| AC3 | From a report I can choose **Approve**, **Reject** or **Request re-upload**. Reject and Re-upload require a comment; submitting without one shows an error. |
| AC4 | After a decision, the case disappears from the default queue and appears under Decided, showing reviewer, time, decision and comment. |
| AC5 | Decisions are never silently overwritten: the stored record keeps who decided and when. |

---

### EP-4 · Accuracy evaluation

#### US-11 · Synthetic dataset generator
*As an **admin**, I want a labelled synthetic dataset of mark sheets and photos, so that accuracy can be measured without real student data.*
**Req:** FR-E01, FR-E02, FR-E03, FR-E04 · NFR-07 · **Size:** M · **Depends on:** template configs (US-05/US-07) · **A first small batch is generated early, because US-05 needs samples.**

| AC | Given / When / Then |
|---|---|
| AC1 | Running the generator creates **40 mark sheets** (20 TN HSC + 20 CBSE XII; each 10 clean + 10 degraded 🔧) and **30 photos**, plus a ground-truth file (JSON/CSV). |
| AC2 | Running it twice produces identical output (fixed random seed). |
| AC3 | Degraded sheets include blur, skew (small), low light and noise. |
| AC4 | Each sheet has a matching "entered marks" record; at least **25 %** of records contain planted errors (mismatch, missing subject, extra subject), all recorded in ground truth. |
| AC5 | The photo set has at least one failing example for every rule P01–P08 and at least 5 fully valid photos. |
| AC6 | All names and numbers are fake; no logos, seals or real data. |

#### US-12 · Run evaluation and show accuracy
*As an **admin**, I want to run the engine over the dataset and see measured accuracy, so that I can prove how reliable the system is.*
**Req:** FR-E05, FR-E06 · NFR-02 · SM-2 – SM-8 · **Size:** M · **Depends on:** US-04, US-06, US-07, US-11, US-09

| AC | Given / When / Then |
|---|---|
| AC1 | A command-line run (`python -m evaluation`) and an **Run evaluation** button (Admin only) both produce the same results. |
| AC2 | Results show: mark extraction accuracy (clean vs. degraded, per template), mismatch detection precision and recall, **false-Match count**, photo-rule accuracy per rule, % sent to review, dataset size and run date. |
| AC3 | A list of every error (file, field, expected, got) is shown, so nothing is hidden. |
| AC4 | If the false-Match count is above 0, the page shows a red warning "Fail-safe broken". (This is a release-blocking bug, SM-2.) |
| AC5 | Figures on the page are labelled "Measured on synthetic data, {date}, n = {size}". |

---

### EP-5 · Platform & demo readiness

#### US-13 · Foundation: database, settings, seed data, error pages
*As the **team**, we want the app to start with demo data, settings and safe error handling, so that the demo always works, even after Render resets the disk.*
**Req:** FR-S04 · NFR-06, NFR-12, NFR-13, NFR-14 · error pages (Phase 2 §8) · **Size:** M · **Depends on:** — (built first, alongside US-04)

| AC | Given / When / Then |
|---|---|
| AC1 | On startup with an empty database, tables are created and seeded with: 1 reviewer + 1 admin demo account, default 🔧 settings, and a set of demo applications (some Auto-cleared, some Needs review). |
| AC2 | Restarting with an existing database does not duplicate seed data. |
| AC3 | 404, 403 and 500 show friendly pages; no stack trace is ever shown to users. |
| AC4 | Secrets (secret key, demo passwords) come from environment variables; nothing secret is committed to Git. |
| AC5 | `docker build` + `docker run` starts the app with Tesseract available, in line with NFR-13. |

---

## 7. Dependencies & build order
```
US-13 Foundation ─┬─► US-04 Photo engine ──────────────┐
                  │                                     │
US-11a first sample sheets ─► US-05 TN HSC OCR ─► US-06 Compare + fail-safe
                  │                                     │
                  ├─► US-01 Details ─► US-02 Upload+Submit ─► US-08 Report ─► US-10 Queue
                  ├─► US-03 Home                               ▲
                  └─► US-09 Login ─────────────────────────────┘
                                     ══ END-TO-END FLOW WORKS (TN HSC) ══
US-07 CBSE XII ─► US-11 full dataset ─► US-12 Evaluation + Accuracy page
                                     ══ D1 + D2 + D3 COMPLETE ══
Optional O-1 … O-9 (only after all 13 pass)
```

**Build order (Phase 6):**
| # | Story | Why here |
|---|---|---|
| 1 | US-13 Foundation | Everything depends on it |
| 2 | US-11a first 5 sample sheets per template | US-05 needs samples |
| 3 | US-04 Photo engine | Low risk; quick confidence win |
| 4 | US-05 TN HSC OCR | **Highest risk**, so tackle early |
| 5 | US-06 Compare + fail-safe | Core of accuracy and safety |
| 6 | US-01 → US-02 → US-03 | Applicant flow |
| 7 | US-09 → US-08 → US-10 | Reviewer flow → **end-to-end works** |
| 8 | US-07 CBSE XII | Second guaranteed template |
| 9 | US-11 full dataset → US-12 Evaluation | D3 |
| 10 | O-1 … O-9 | Only if time remains |

---

## 8. Timeline (4 days × 1–2 h team time)
| Day | Claude does | Team does (≈1–2 h) | Exit check |
|---|---|---|---|
| **1** | Phases 1–3 docs ✅ | Approve backlog | Backlog approved |
| **2** | Phase 4 design, Phase 5 setup + **early Render speed test**, US-13, US-11a, US-04, US-05 | Approve design (20 min); run app locally once (20 min); check photo + OCR test results (20 min) | Photo tests pass; TN HSC samples read correctly |
| **3** | US-06, US-01–03, US-09, US-08, US-10 | Test each story against its ACs as it lands (~10 min each) | **End-to-end flow works locally** |
| **4** | US-07, US-11, US-12, Phase 7 QA, Phase 8 deploy, Phase 9 slides | Run QA checklist; check live site; rehearse demo | All 4 release gates pass on deployed site |

**Honest risk:** Day 3 is the heaviest. If US-05 (OCR) takes longer on Day 2, Day 3 slips. **Cut order if behind:** optional items first (already excluded) → print/visual polish → reduce dataset to 20 sheets (10 per template, still clean + degraded, clearly labelled with n). **Never cut:** fail-safe tests (US-06), degraded data, the false-Match check.

---

## 9. Traceability matrix (every Must requirement → story)
| Requirement | Story | | Requirement | Story |
|---|---|---|---|---|
| FR-A01 | US-01 | | FR-R01 | US-06, US-08 |
| FR-A02 | US-01 | | FR-R02 | US-08 |
| FR-A03 | US-01 | | FR-R03 | US-08 |
| FR-A04 | US-01, US-02 | | FR-R04 | US-08 |
| FR-A05 | US-02 | | FR-R05 | US-08 |
| FR-A06 | US-02 | | FR-R07 | US-08 |
| FR-A10 | US-02 | | FR-Q01 | US-10 |
| FR-A11 | US-03 | | FR-Q02 | US-10 |
| FR-V01 | US-05 | | FR-Q03 | US-10 |
| FR-V02 | US-05 | | FR-Q04 | US-10 |
| FR-V03 | US-05, US-07 | | FR-E01 | US-11 |
| FR-V04 | US-05, US-07 | | FR-E02 | US-11 |
| FR-V06 | US-06 | | FR-E03 | US-11 |
| FR-V07 | US-06 | | FR-E04 | US-11 |
| FR-V08 | US-06 | | FR-E05 | US-12 |
| FR-V11 | US-06 | | FR-E06 | US-12 |
| FR-P01–P08 | US-04 | | FR-S01 | US-09 |
| | | | FR-S02 | US-09 |
| | | | FR-S04 | US-13 |

**Coverage: 43 / 43 Must functional requirements mapped.**

**Non-functional requirements → where verified**
| NFR | Story / phase |
|---|---|
| NFR-01 Performance | Phase 5 speed test, Phase 7 (SM-9) |
| NFR-02 Accuracy | US-06, US-12 (SM-2, SM-4, SM-6) |
| NFR-03 Fail-safe | US-04 AC6, US-06 AC5–7, US-12 AC4 |
| NFR-04 Explainability | US-04 AC1, US-08 AC2 |
| NFR-05 No GenAI | US-04, US-05; dependency check in Phase 7 |
| NFR-06 Security | US-02 AC6, US-09, US-13 AC4 |
| NFR-07 Privacy | US-02 AC6, US-11 AC6 |
| NFR-08 Usability | US-01, US-02, US-03 |
| NFR-09 Accessibility | US-01 AC6, US-08 AC4; Phase 7 check |
| NFR-10 Responsive | US-01 AC6, US-08 AC3; Phase 7 check |
| NFR-11 Browsers | Phase 7 |
| NFR-12 Maintainability | US-05 AC4, US-13; README in Phase 8 (SM-11) |
| NFR-13 Deployability | US-13 AC5, Phase 8 |
| NFR-14 Reliability | US-13 AC1–3 |

---

## 10. Definition of Ready / Done
**Ready** (before a story is built): ACs agreed · dependencies done · test data available.
**Done** (before moving to the next story):
1. Code written for **this story only** (no unapproved features).
2. Automated tests written (engine stories test-first) and passing.
3. Every AC checked and recorded **PASS / FAIL / NOT TESTED** in the QA checklist.
4. No previously passing test broken.
5. Team member (QA) has seen it work.

---

## Critical review of this phase
1. **Essential scope is still substantial** (13 stories in ~4–8 team hours). It works only because Claude builds and the team verifies. The plan protects itself with a fixed build order, an end-to-end checkpoint on Day 3, and a written cut order that never touches accuracy or the fail-safe.
2. **US-05 (OCR) is the single biggest risk.** It is scheduled early and gated by AC5 on 5 sample sheets. If it fails, we learn on Day 2, not Day 4.
3. **Synthetic sheets are generated by us**, so OCR may look better than on real sheets. Mitigated by degraded variants, separate figures, and the "measured on synthetic data" label (US-12 AC5).
4. **Release gates are strict on purpose:** SM-2 (zero false Match) and SM-3 (100 % routing of uncertain cases) are the system's core promise.
5. **Open item (non-blocking):** Maatram's real photo rules and volumes remain 🔧 / ⏳.
