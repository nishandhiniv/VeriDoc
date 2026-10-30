# VeriDoc: Smart Admission Document Validation

**Maatram HackForge 2026–27 · Problem MH26-01 · Software track**

VeriDoc checks admission applications automatically:

- **Marks.** It reads the uploaded mark sheet (TN State Board HSC or CBSE Class XII) with OCR and compares each subject's total with the mark the applicant typed.
- **Photo.** It checks the profile photo against measurable rules: format, file size, resolution, maximum size, aspect ratio, orientation, brightness and sharpness.

Applications where everything checks out are **auto-cleared**. Anything wrong *or uncertain* goes to a **manual-review queue**. The system never rejects anyone on its own.

> Prototype. Synthetic data only: do not upload real students' documents.

| Deliverable (from the problem statement) | Where |
|---|---|
| D1 · Validation report for each application | Staff → Review queue → open any application |
| D2 · Manual-review queue for exceptions | Staff → Review queue (Needs review / Auto-cleared / Decided) |
| D3 · Accuracy results on sample mark sheets and photos | Staff (admin) → Accuracy, or `python -m evaluation` |

**No Generative AI or LLMs are used in validation.** The engine uses Tesseract OCR, OpenCV, Pillow, fuzzy string matching (RapidFuzz) and plain rules.

---

## Run it in under 5 minutes (Docker)

You need [Docker](https://docs.docker.com/get-docker/).

```bash
git clone <this repository> veridoc && cd veridoc
```

```bash
docker build -t veridoc .
```

```bash
docker run --rm -p 8000:10000 -e DEMO_REVIEWER_PASSWORD=review-demo -e DEMO_ADMIN_PASSWORD=admin-demo veridoc
```

Open <http://localhost:8000>. Within about a minute the app fills itself with 8 demo applications. A first accuracy run follows in the background and takes a few minutes.

| Account | Email | Password |
|---|---|---|
| Reviewer | `reviewer@veridoc.test` | the `DEMO_REVIEWER_PASSWORD` you set |
| Admin | `admin@veridoc.test` | the `DEMO_ADMIN_PASSWORD` you set |

If you don't set a password, a random one is generated and printed in the container log. No default password is ever built in.

## Run it without Docker (for development)

You need Python 3.11+ and Tesseract 5. On Ubuntu or Debian, install Tesseract with `sudo apt install tesseract-ocr`.

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
```

```bash
DEMO_REVIEWER_PASSWORD=review-demo DEMO_ADMIN_PASSWORD=admin-demo flask --app wsgi run
```

Then run the tests:

```bash
python -m pytest
```

## A 3-minute demo

1. **Home → Start application.** Use the synthetic files in [`samples/`](samples/): its README lists the name and marks printed on each sheet. Type one mark wrong on purpose to see a mismatch.
2. **Check and submit** → you get a reference number such as `VD-2026-00009`.
3. **Staff sign in** as the reviewer → **Review queue** → open an application marked *Needs review*:
   - mismatched marks show `Entered: 80, Uploaded: 77`
   - a small photo shows `Fail · 180 × 220 px · minimum 300 × 400 px`
4. Choose **Request re-upload**, add a comment → the case moves to *Decided*, with your name and the time recorded.
5. Sign in as the admin → **Accuracy** → see the measured results, or press **Run evaluation**.

## How validation works

```
mark sheet ─► OpenCV: grayscale, upscale to ~300 dpi, even out lighting, Otsu threshold
           ─► Tesseract: words + positions + confidence
           ─► template profile (JSON): find the title, the header and the mark column
           ─► subject names: fuzzy match to the template's aliases ("MATHS" → Mathematics)
           ─► each mark re-read digits-only; both readings must agree
           ─► compare with the entered marks: Match / Mismatch / Missing / Not entered / Unreadable
photo      ─► Pillow + OpenCV measurements ─► 8 rule checks with configurable thresholds
```

**Fail-safe rule.** An application is *auto-cleared* only when every check is clean. Any of these send it to *Needs review*, never to "Match" or "Pass":
- low OCR confidence (even when the digits happen to agree)
- two readings that disagree
- an unrecognised layout
- a processing error

Every threshold (photo rules, OCR confidence, mark tolerance) is a setting stored in the database. All of them are **defaults chosen by the team, pending confirmation by Maatram**, except the 300 × 400 minimum, which comes from the problem statement's example.

## Accuracy (D3)

Run `python -m evaluation` to:
1. generate the synthetic dataset, if it doesn't exist yet
2. run the engine on it
3. print the report

The admin **Accuracy** page shows the same numbers.

- **Dataset:** 40 mark sheets (20 TN HSC + 20 CBSE XII, each half clean and half degraded with blur, skew, low light, noise and JPEG artefacts) and 30 labelled photos. 40 % of applications contain planted errors.
- **Ground truth** comes from the generator's own parameters, never from the engine.
- **What the numbers mean:** the engine was developed on sheets from the same generator. The results show the method works on these templates. They are **not** a claim about accuracy on real mark sheets.
- **Robustness:** `python -m evaluation.stress` runs a held-out seed with harsher damage, to show where reading stops being confident and that the fail-safe still holds.

## Project layout

```
app/          Flask web app: applicant pages, staff pages, models, seeding
engine/       Validation engine (no web code): photo.py, marksheet.py, validate.py, templates/*.json
dataset/      Synthetic mark sheet and photo generator with ground truth
evaluation/   Accuracy evaluation (D3) and robustness probe
tests/        pytest suite, organised by user story
docs/         Phase 1–4 documents: problem, requirements, backlog, design
Dockerfile    App + Tesseract in one image; render.yaml deploys it to Render
```

## Deploying to Render (free plan)

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint**, pick the repository, and enter the two demo passwords when asked.
3. Render builds the Dockerfile and gives the service a public URL.

The free plan sleeps when idle, so the first visit takes about a minute. Its disk also resets on restart, which is why demo data and the first accuracy run are recreated automatically on startup.

## Limitations

- Only the synthetic TN HSC and CBSE XII layouts are supported. Other layouts are sent to manual review.
- Printed mark sheets only. No PDF upload yet (planned enhancement).
- Photo checks are measurements. They can't tell whether the photo shows the applicant.
- SQLite and local file storage suit a prototype. Production would need a managed database and file storage.
