# Phase 2 – Requirements Document
**Project:** MH26-01 · Smart Admission Document Validation (working name: VeriDoc)
**Event:** Maatram HackForge 2026–27
**Based on:** `01-problem-analysis.md` (approved). All Phase 1 decisions are kept unchanged.
**Status:** ✅ APPROVED – Revision 2 (fixes E1–E6, T1–T3; see §13)

**Legend**
- 🔧 **CONFIGURABLE / PENDING CONFIRMATION**: a default chosen by us, not confirmed by Maatram. Stored as a setting, never hard-coded.
- **Priority** (provisional, finalised in Phase 3): **M** = Must · **S** = Should · **C** = Could
- **Deliverables:** **D1** validation report · **D2** manual-review queue · **D3** accuracy results

---

## 1. Users and personas
The personas are **fictional** and built from the problem statement. They are not based on research with real Maatram users (assumption A-P1).

### P1 · Applicant: "Priya", 17, Class 12 student (TN State Board)
- Applies from a **budget Android phone** on mobile data. Her mark sheet photo is taken on a table under a tube light.
- Not sure what photo size is "correct". Typed one mark wrong last year on another form and only found out weeks later.
- **Goal:** submit once, correctly, and know straight away whether anything is wrong.

### P2 · Reviewer: "Karthik", admission volunteer / staff member
- Checks applications on a laptop, often in batches in the evening.
- Today he opens every mark sheet and compares it line by line with the form.
- **Goal:** look only at applications with a real problem, see *exactly* which field is wrong, and decide in under a minute.

### P3 · Admin: "Meena", programme coordinator
- Owns the admission rules: which boards are accepted, what photo is acceptable.
- Has to explain the process to management and trust the automation before using it.
- **Goal:** adjust rules without a developer, and see **measured** proof of how accurate the system is.

---

## 2. User needs and pain points
| Persona | Pain point today | Need | Requirement IDs |
|---|---|---|---|
| Applicant | Doesn't know photo rules; finds out late | Clear rules up front + instant photo feedback | FR-A11, FR-A07 |
| Applicant | Typing mistakes go unnoticed | Review screen before submitting + inline form errors | FR-A10, FR-A04 |
| Applicant | No idea what happens after submitting | A reference number and status page | FR-A06, FR-A08 |
| Reviewer | Every application checked by eye | Automatic check; clean ones cleared | FR-V*, FR-R01 |
| Reviewer | Hard to see *what* is wrong | Field-level Entered vs. Uploaded view with reasons | FR-R02–R04 |
| Reviewer | No record of decisions | Decision + comment + timestamp per case | FR-Q03–Q05 |
| Admin | Rules live in people's heads | Editable settings for photo rules and thresholds | FR-S03 |
| Admin | Can't trust "black box" automation | Accuracy report measured on labelled data; every result explains its rule | FR-E*, NFR-04 |

---

## 3. User journeys

### J1 · Applicant submits an application (no login)
1. Opens the site → **Home** page explains what's needed (mark sheet, photo, photo rules).
2. Clicks **Start application** → enters name, date of birth, email/phone, **board + exam** (e.g. "TN HSC", "CBSE XII"), **register/roll number**.
3. The form shows the **subject list for that board**. Applicant picks their subjects and types the **total mark** for each.
4. Uploads the **mark sheet** (JPG/PNG image; PDF is a Should, FR-A12) and **profile photo**.
5. *(Should)* Photo is checked instantly. Problems are shown with how to fix them ("Photo is 180×220 px; minimum is 300×400 px"). This is a warning only; it never blocks submission.
6. **Review screen** shows everything typed → **Submit**.
7. System runs validation (D1) → applicant sees a **confirmation page with reference number** (e.g. `VD-2026-00042`).
8. *(Should)* Applicant can check status later using reference number + date of birth.

### J2 · Reviewer handles exceptions (login required)
1. Logs in → **Dashboard**: counts of *Auto-cleared*, *Needs review*, *Decided*.
2. Opens **Review queue** (D2), filtered to *Needs review* by default, sorted oldest first.
3. Opens an application → **Validation report** (D1): Entered vs. Uploaded table, photo checks, reasons, mark sheet image beside it.
4. Chooses **Approve**, **Reject**, or **Request re-upload**, adds a comment (required for Reject / Re-upload).
5. The case leaves the queue; the decision is logged with who and when.

### J3 · Admin configures and measures (login required)
1. Logs in → **Settings**: edits photo rules and OCR confidence threshold (🔧 values).
2. Opens **Accuracy** page (D3) → clicks **Run evaluation** on the synthetic dataset.
3. Sees measured results: per-field extraction accuracy, mismatch detection, photo-check accuracy, % sent to review, and a list of every error.
4. Can download the results (CSV) for the presentation.

---

## 4. Functional requirements

### 4.1 Applicant workflow
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-A01 | Applicant can start an application without an account. | M | D1 |
| FR-A02 | Form collects: full name, date of birth, contact (email or phone), board + exam type, register number, and subject marks. All required. | M | D1 |
| FR-A03 | Choosing the board/exam shows that template's **subject list**. Applicant selects their subjects (min/max count per template) and enters the **total mark** per subject (whole number, 0 to the subject's maximum). | M | D1 |
| FR-A04 | Form validates **input** before submit: required fields, number ranges, no duplicate subjects. Files are blocked **only if they cannot be processed at all** (not an image, or above the hard upload cap of 10 MB). All photo **rules** (format, size, dimensions, etc.) are checked by the engine and shown in the report, never blocked by the form. Errors are shown next to the field in plain language. | M | D1 |
| FR-A05 | Applicant uploads one mark sheet (JPG/PNG) and one photo (any image). File type is detected by **content**, not only by file name. | M | D1 |
| FR-A06 | After submit, the applicant sees a confirmation page with a unique reference number. | M | D1 |
| FR-A07 | Instant photo pre-check before submit, with fix-it messages. **Warns only, never blocks** (see FR-A04). | S | D1 |
| FR-A08 | Status page: reference number + date of birth shows status (Received / Under review / Approved / Rejected / Re-upload requested). | S | D2 |
| FR-A09 | Re-upload flow: when a reviewer requests it, the applicant can replace the file using the reference number, and validation re-runs. | C | D2 |
| FR-A10 | **Review screen** before Submit shows everything entered (details, subjects + marks, file names and thumbnails) with an **Edit** link per section. | M | D1 |
| FR-A11 | **Home page** lists the documents needed and the **current photo rules**, read from Settings (so the page and the checks never disagree). | M | D1 |
| FR-A12 | Mark sheet may also be uploaded as **PDF** (first page used). | S | D1 |

### 4.2 Mark sheet validation (core engine, no GenAI/LLM)
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-V01 | Pre-process the mark sheet image: grayscale, denoise, threshold (OpenCV). | M | D1 |
| FR-V02 | Run OCR (Tesseract) and keep word-level **confidence** scores. | M | D1 |
| FR-V03 | Parse **subject → total mark** pairs using the **template profile** for the selected board/exam (subject names + aliases, mark column rules, regex). Fuzzy matching for subject names (e.g. "MATHS" ↔ "Mathematics"). | M | D1 |
| FR-V04 | Templates: **TN HSC** and **CBSE XII** guaranteed. | M | D1 |
| FR-V05 | Templates: **TN SSLC** and **CBSE X**, added as configuration once V03 works. | S | D1 |
| FR-V06 | For each entered subject, result is one of: **Match** (equal), **Mismatch** (different; show both values), **Missing on sheet** (subject not found), **Unreadable (low OCR confidence)** (confidence below threshold 🔧). | M | D1 |
| FR-V07 | Subjects found on the sheet but **not entered** by the applicant are flagged **Not entered**. | M | D1 |
| FR-V08 | **Completeness check:** pass only if every entered subject is found and none are left over. | M | D1 |
| FR-V09 | **Identity fields:** compare register number (exact) and name (fuzzy, 🔧 threshold) against the sheet. | S | D1 |
| FR-V10 | **Total check:** sum of extracted subject marks equals the total printed on the sheet (if present). | C | D1 |
| FR-V11 | Unknown layout (template not recognised / too few subjects parsed) → whole mark-sheet section = **Needs review**, never auto-pass. | M | D1 |
| FR-V12 | Extra pre-processing: **de-skew** rotated scans, and convert PDF page 1 to an image (with FR-A12). | S | D1 |

### 4.3 Photo validation (deterministic measurements)
All thresholds come from **Settings** (see §5). Each check returns Pass/Fail with the measured value and the rule.

| ID | Check | Priority | Deliverable |
|---|---|---|---|
| FR-P01 | **File format** (by content): JPEG or PNG | M | D1 |
| FR-P02 | **File size** within min/max | M | D1 |
| FR-P03 | **Resolution**: width × height ≥ minimum | M | D1 |
| FR-P04 | **Maximum dimensions**: width × height ≤ maximum | M | D1 |
| FR-P05 | **Aspect ratio** (width ÷ height) within accepted range | M | D1 |
| FR-P06 | **Orientation**: portrait (after applying EXIF rotation) | M | D1 |
| FR-P07 | **Brightness**: mean brightness within range (not too dark/washed out) | M | D1 |
| FR-P08 | **Sharpness**: blur score (variance of Laplacian) ≥ minimum | M | D1 |
| FR-P09 | **Contrast**: pixel standard deviation ≥ minimum | S | D1 |
| FR-P10 | **Face present**: exactly one face detected (OpenCV Haar cascade, classical CV, not GenAI) | C | D1 |

### 4.4 Validation report (D1)
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-R01 | Every submitted application gets an **overall status**: **Auto-cleared** (all checks Pass/Match) or **Needs review** (any Fail, Mismatch, Missing, Not entered, Unreadable, or unknown layout). These are the **only two automatic outcomes: the system never auto-rejects.** Approve / Reject / Re-upload are human decisions (FR-Q03). | M | D1, D2 |
| FR-R02 | Report table in the catalogue format: **Validation · Result · Details**, e.g. "Mathematics Marks · ❌ Mismatch · Entered: 85, Uploaded: 88". | M | D1 |
| FR-R03 | Each row shows the **reason / rule** used (e.g. "minimum 300 × 400") and, for marks, the OCR confidence. | M | D1 |
| FR-R04 | Report page shows the uploaded mark sheet and photo next to the table. | M | D1 |
| FR-R05 | Results use **icon + text + colour** (never colour alone). | M | D1 |
| FR-R06 | Report can be printed / saved as PDF via a print-friendly layout. | S | D1 |
| FR-R07 | Results are stored, so reopening a report does not re-run OCR. | M | D1 |

### 4.5 Manual-review queue (D2)
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-Q01 | Queue lists applications with reference, name, board, submitted time, overall status and **number of issues**. | M | D2 |
| FR-Q02 | Filter by status (Needs review / Auto-cleared / Decided). Default view: Needs review, oldest first. | M | D2 |
| FR-Q03 | Reviewer decision: **Approve**, **Reject**, or **Request re-upload**. Comment required for Reject and Re-upload. | M | D2 |
| FR-Q04 | Each decision stores reviewer, timestamp, decision, comment (audit trail). Decided cases leave the default queue. | M | D2 |
| FR-Q05 | Reviewer can also override an auto-cleared case (e.g. spot-check) with the same decision options. | S | D2 |
| FR-Q06 | Dashboard shows counts per status. | S | D2 |
| FR-Q07 | Export queue/decisions to CSV. | C | D2 |
| FR-Q08 | Filter by board; search by reference number or name. | S | D2 |

### 4.6 Accuracy evaluation (D3)
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-E01 | A **synthetic dataset generator** creates mark sheets per template with **known correct values** (ground truth) and fake names. No real student data, logos or seals. Size: **40 mark sheets** = 20 per guaranteed template (TN HSC, CBSE XII), each 10 clean + 10 degraded 🔧. Generation is repeatable (fixed random seed). | M | D3 |
| FR-E02 | Dataset includes **clean** and **degraded** variants (blur, skew, low light, phone-photo noise) so accuracy is not only measured on perfect images. | M | D3 |
| FR-E03 | Each synthetic application also has **entered marks** with deliberately planted errors (known mismatches, missing subjects) to test detection. | M | D3 |
| FR-E04 | A synthetic **photo set** of **30 photos** 🔧 with known labels (e.g. too small, wrong ratio, too dark, blurry, landscape, valid), covering every Must photo rule (FR-P01–P08) with at least one failing example each. | M | D3 |
| FR-E05 | **Evaluation run** compares system output with ground truth and reports: (a) mark extraction accuracy per field, (b) mismatch detection precision and recall, (c) photo-check accuracy per rule, (d) % of applications sent to review, (e) list of every error. Separate figures for clean vs. degraded. | M | D3 |
| FR-E06 | Accuracy page in the app shows the latest run (date, dataset size, metrics, errors). Can also run from command line. | M | D3 |
| FR-E07 | Export results to CSV / Markdown for the presentation. | S | D3 |

> **Honesty rule:** accuracy figures are only ever **measured** results of FR-E05 on our synthetic dataset, always shown with dataset size and date. They are not claims about real-world mark sheets.

### 4.7 Settings, users and access
| ID | Requirement | Priority | Deliverable |
|---|---|---|---|
| FR-S01 | Reviewer and Admin log in with email + password. Applicants never need an account. | M | D2 |
| FR-S02 | **Roles:** Reviewer = dashboard, queue, reports, decisions. Admin = everything Reviewer can + Settings + Accuracy. Pages check the role on the server. | M | D2 |
| FR-S03 | Admin can edit all 🔧 photo and OCR settings in a Settings page. Changes apply to new validations. | S | D1 |
| FR-S04 | Demo accounts and demo applications are **seeded on startup** (needed because Render's free disk resets). | M | D1, D2, D3 |
| FR-S05 | Admin can add/edit template subject lists in the UI. *(Until then: edited in a config file.)* | C | D1 |

---

## 5. Configurable settings (🔧 pending confirmation by Maatram)
None of these values were provided by Maatram. Only the **300 × 400 minimum** comes from the catalogue's example report. All others are **our starting defaults** and can be changed in Settings (FR-S03) or config.

| Setting | Default | Source |
|---|---|---|
| Photo formats allowed | JPEG, PNG | Catalogue example shows JPEG; PNG added by us 🔧 |
| Photo file size | 20 KB – 2 MB | 🔧 our default |
| Photo minimum dimensions | 300 × 400 px | Catalogue example 🔧 |
| Photo maximum dimensions | 3000 × 4000 px | 🔧 our default |
| Photo aspect ratio (w ÷ h) | 0.70 – 0.85 (around passport 3:4 / 35×45 mm) | 🔧 our default |
| Photo orientation | Portrait | 🔧 our default |
| Brightness (mean, 0–255) | 70 – 210 | 🔧 our default, tuned on synthetic set |
| Sharpness (variance of Laplacian) | ≥ 60 | 🔧 our default, tuned on synthetic set |
| Contrast (std dev, 0–255) | ≥ 25 | 🔧 our default |
| Mark sheet file types / size | JPG, PNG (PDF only with FR-A12) · ≤ 5 MB | 🔧 our default |
| Hard upload cap (any file) | 10 MB, blocks at the form | 🔧 our default (technical limit, not a photo rule) |
| OCR confidence threshold | 70 (0–100) | 🔧 our default, tuned on synthetic set |
| Mark tolerance | 0 (exact match) | Phase 1 assumption A4 🔧 |
| Name match threshold | 85 % similarity | 🔧 our default |
| Evaluation dataset size | 40 mark sheets · 30 photos | 🔧 our default (FR-E01, FR-E04) |

**Application volumes: ⏳ PENDING CONFIRMATION.** We do not know how many applications Maatram receives. The prototype is **not** sized for a specific number. Performance targets in §6 are per-application, and the demo uses seeded synthetic data.

---

## 6. Non-functional requirements
| ID | Category | Requirement (testable) |
|---|---|---|
| NFR-01 | Performance | Validation of one application completes in **≤ 20 s** on the deployed server (a target, not a claim). Render free plan has very limited CPU, so a **deployment speed test is done early in Phase 5**, and the result is measured again in Phase 7. Pages other than submit load in ≤ 3 s after the server is awake. |
| NFR-02 | Accuracy target | Goal: **≥ 95 % mark extraction accuracy on clean synthetic sheets**, and **zero false "Match"** on planted mismatches when OCR is confident. Actual numbers are reported as measured, whether or not the goal is met. |
| NFR-03 | Fail-safe | Any uncertainty (low confidence, unknown layout, processing error) → **Needs review**. The system never auto-clears on error. |
| NFR-04 | Explainability | Every result shows its rule and measured value. No hidden scoring. |
| NFR-05 | No GenAI | Core validation uses only OCR, OpenCV, Pillow, rules and statistics. No LLM/GenAI libraries in `requirements.txt` of the validation engine. |
| NFR-06 | Security | Passwords hashed; server-side role checks on every protected page; CSRF protection on forms; uploads checked by content type and size; random server-side file names; secrets in environment variables, never in Git. |
| NFR-07 | Privacy | Only synthetic data in the repo, dataset and demo. A visible "Prototype – do not upload real documents" notice on the form. |
| NFR-08 | Usability | Applicant can complete the form without help; every error message says what is wrong and how to fix it. |
| NFR-09 | Accessibility | WCAG 2.1 AA basics: labels on all inputs, keyboard navigation, visible focus, colour contrast ≥ 4.5:1, status never by colour alone. |
| NFR-10 | Responsive | Applicant pages work at 360 px (phone), 768 px (tablet), 1280 px+ (desktop). Reviewer pages are optimised for desktop and usable on tablet. |
| NFR-11 | Browsers | Latest Chrome, Edge, Firefox; Chrome on Android. |
| NFR-12 | Maintainability | One language (Python); templates/rules in config; automated tests for the validation engine; README lets a stranger run it in ≤ 5 minutes with Docker. |
| NFR-13 | Deployability | Single Docker image (app + Tesseract) deployable to Render's free plan from GitHub. |
| NFR-14 | Reliability | Seed data recreated on startup (FR-S04); errors logged; user sees a friendly error page, never a stack trace. |

---

## 7. Existing alternatives and how we improve
| Alternative | Limitation | Our improvement |
|---|---|---|
| **Manual checking** (current) | Slow; mistakes missed; no record | Automatic checks; only exceptions reach a human; audit trail |
| **Basic form validation** (required fields, file type) | Doesn't compare typed marks with the document | Field-level Entered vs. Uploaded comparison |
| **Commercial document-AI / KYC services** | Paid, data sent to third parties, often GenAI-based (not allowed here) | Free, self-hosted, deterministic and explainable |
| **DigiLocker / board verification** | Verifies authenticity where available, but needs official integration | Out of scope now; listed as a **future improvement** |

---

## 8. Essential website features (pages)
| Page | Users | Priority |
|---|---|---|
| Home / instructions (incl. photo rules) | Applicant | M |
| Application form (multi-step: details → marks → uploads → review) | Applicant | M |
| Submission confirmation (reference number) | Applicant | M |
| Application status lookup | Applicant | S |
| Login | Reviewer, Admin | M |
| Dashboard (status counts) | Reviewer, Admin | S |
| Review queue | Reviewer, Admin | M |
| Application validation report + decision panel | Reviewer, Admin | M |
| Accuracy report | Admin | M |
| Settings | Admin | S |
| Error pages (404 / 403 / 500) | All | M |

---

## 9. Technical requirements
*(Stack confirmed in Phase 1; architecture detailed in Phase 5.)*
- **Backend:** Python 3.11+, Flask, Jinja2 templates, Flask-Login, Flask-WTF (forms + CSRF), SQLAlchemy.
- **Database:** SQLite (single file). Main tables, provisional: users, applications, entered_marks, uploads, validation_results, decisions, settings, evaluation_runs.
- **Validation engine:** separate Python package (`engine/`), usable without the website: OpenCV, Pillow, pytesseract, RapidFuzz (fuzzy text matching, not AI), PyMuPDF for PDFs (only if FR-A12 is built).
- **Templates:** one config file per board/exam (subjects, aliases, max marks, parsing hints).
- **Dataset tools:** Pillow-based synthetic mark sheet + photo generator; evaluation script.
- **Testing:** pytest (engine + routes), Playwright (end-to-end).
- **Deployment:** Dockerfile (installs Tesseract), Render free plan, GitHub repo.
- **Validation runs synchronously** on submit (no background queue), which keeps the system simple. Acceptable while NFR-01 holds.

---

## 10. Limitations
- Works for **our synthetic templates** of TN and CBSE layouts. Real mark sheets may differ and would go to review until a template is tuned.
- Printed mark sheets only; handwriting not supported.
- Photo "quality" means measurable properties. It cannot tell whether the photo shows the applicant.
- Render free plan: sleeps when idle; database and uploads reset on restart (seeded demo data covers the demo).
- SQLite suits a prototype, not many simultaneous reviewers.
- Accuracy results describe our synthetic dataset only.

## 11. Out of scope (Won't have, this version)
- Any GenAI/LLM in validation
- Real student documents
- Applicant accounts / login
- Face recognition or identity verification (face *detection* FR-P10 is only a Could)
- Handwritten mark sheets; boards other than TN State Board and CBSE
- Authenticity / forgery checks, DigiLocker or board integration
- Email/SMS notifications, payments, multi-language UI, mobile app

---

## 12. Requirement summary
| Priority | Functional | IDs |
|---|---|---|
| **M** | 43 | A01–A06, A10, A11, V01–V04, V06–V08, V11, P01–P08, R01–R05, R07, Q01–Q04, E01–E06, S01, S02, S04 |
| **S** | 13 | A07, A08, A12, V05, V09, V12, P09, R06, Q05, Q06, Q08, E07, S03 |
| **C** | 5 | A09, V10, P10, Q07, S05 |
| NFR | 14 | NFR-01 … NFR-14 (all apply to the Must-Have scope) |

> ⚠️ 43 functional Must requirements is a lot for 4 days (two were **added** by E2/E3; T1 made three of them **smaller** by moving PDF, de-skew, search and board filter into new Should items). They are all **parts of the 3 Must-Have features** (D1, D2, D3), not separate features. Phase 3 will group them into 3–5 epics and 8–15 stories and may move some to Should if the backlog is too large.

---

## 13. Revision log
| Rev | Change | Reason |
|---|---|---|
| 2 | E1: corrected requirement IDs in §2 | Wrong cross-references |
| 2 | E2: added FR-A10 review screen (M) | Journey step had no requirement |
| 2 | E3: added FR-A11 home page with live photo rules (M) | Page had no requirement |
| 2 | E4: form blocks only unprocessable files; all photo rules reported by engine; A07 warns only | Form and report contradicted each other |
| 2 | E5: "Unreadable (low OCR confidence)"; system never auto-rejects | Terminology aligned with Phase 1 |
| 2 | E6: Phase 1 §15 now says 2 guaranteed + 2 Should templates | Phase 1 internal contradiction |
| 2 | T1: PDF → FR-A12 (S); de-skew → FR-V12 (S); search + board filter → FR-Q08 (S) | 4–8 h time budget |
| 2 | T2: early deployment speed test in Phase 5 (NFR-01) | Unproven performance on Render free plan |
| 2 | T3: dataset fixed at 40 mark sheets + 30 photos (🔧) | Makes D3 scope concrete |

## Critical review of this phase
1. **Biggest risk is still OCR parsing (FR-V03).** Requirements keep it safe: anything uncertain becomes *Needs review* (NFR-03), so a weak parser lowers automation but never produces wrong "Match" results.
2. **Synthetic data could make accuracy look too good.** Degraded variants (FR-E02) and separate clean/degraded figures address this, and the honesty rule forbids presenting the numbers as real-world accuracy.
3. **CBSE theory/practical split:** the form asks for the subject **total**, and the template must read the total column, not theory marks. To be covered by tests.
4. **TN HSC subject choice varies by stream:** handled by letting applicants choose subjects from the template list (FR-A03) instead of a fixed list.
5. **Missing for later confirmation (non-blocking):** real photo rules and application volumes from Maatram (§5).
6. **Scope watch:** Should items (A07 photo pre-check, A08 status page, S03 settings) give strong UX/demo value. They are the first to build after the Musts, and the first to cut if time runs short.
