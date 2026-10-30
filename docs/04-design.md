# Phase 4 – UI/UX Design
**Status:** Built under the team's instruction to complete the project end to end. The design is reviewed through screenshots in Phase 7.
**Method:** `frontend-design` skill (plan → review against the brief → build → critique).

## 1. Brief
- **Subject:** checking admission documents for an education non-profit. The work is careful clerical comparison of numbers on official paper.
- **Audiences:**
  - Applicants: students on budget phones, often anxious, filling in a form once.
  - Reviewers and admins: staff on laptops doing repeated triage work.
- **Primary job:** make **differences between typed and printed values impossible to miss**, and make "unsure" visibly different from "fine".

## 2. Design direction: "Mark sheet ledger"
The interface borrows from the object being checked, a printed mark sheet: ruled rows, tabular figures and clear columns. One accent is reserved for status. It is calm and procedural, not a marketing look.

Rejected defaults (generic AI-app looks): cream background with terracotta accent; dark mode with acid accent; identical rounded cards with soft shadows everywhere; ALL-CAPS eyebrow labels; monospace labels; "→" on every button.

## 3. Tokens
| Token | Value | Use |
|---|---|---|
| `--ink` | `#16212B` | Text |
| `--ink-2` | `#4F5D69` | Secondary text (contrast 6.6:1 on white) |
| `--paper` | `#FFFFFF` | Page and table background |
| `--wash` | `#EEF2F1` | Page band and ruled-row alternation |
| `--rule` | `#C9D3D1` | Table rules, input borders |
| `--brand` | `#0B5F55` | Primary buttons, links, focus (ledger green, 7.5:1) |
| `--ok` | `#1D6B34` | Match / Pass |
| `--bad` | `#A8251B` | Mismatch / Fail |
| `--warn` | `#8A5A00` | Needs review / Unreadable |
| `--info` | `#2350A0` | Neutral notices |

- **Type:** **Public Sans** (a plain, institutional sans), with a system-font fallback. Figures use `font-variant-numeric: tabular-nums` so marks line up.
- **Scale:** 14 / 16 / 20 / 26 / 34 px. Body text 16 px, line height 1.5, line length ≤ 70 characters.
- **Space:** 4-px base (4, 8, 12, 16, 24, 32, 48).
- **Radius:** 4 px on inputs and buttons only. Tables and panels are square and ruled, like the paper they mirror.
- **Status badges:** always **icon + word + colour**:
  - ✓ Match
  - ✕ Mismatch
  - ! Unreadable
  - ? Missing
  - \+ Not entered
  - ✓ Pass
  - ✕ Fail
  - ! Processing error

## 4. Screens and navigation
```
Public:  Home ─► Apply (1 Details & marks → 2 Uploads → 3 Review) ─► Submitted (reference)
Staff:   Login ─► Queue ─► Application report (+ decision panel)
Admin:   + Accuracy
```
| Screen | Story | Layout |
|---|---|---|
| Home | US-03 | Single column. What you need, and photo rules as a ruled table. Start button. |
| Apply · step 1 | US-01 | Step indicator (real sequence, so numbers are justified). Details fields, board select, subject rows (select + mark + remove), "Add subject". |
| Apply · step 2 | US-02 | Two file inputs with live thumbnail preview. Prototype notice. |
| Apply · step 3 | US-02 | Read-only summary, an Edit link per section, Submit. |
| Submitted | US-02 | Reference number large and selectable, plus what happens next. |
| Login | US-09 | Narrow form. |
| Queue | US-10 | Status tabs (Needs review / Auto-cleared / Decided) with counts, then a ruled table. |
| Report | US-08 | **Desktop:** check table (left 60%) and documents (right 40%, sticky). **Mobile:** stacked. Decision panel under the table. |
| Accuracy | US-12 | Run button, metric rows (clean vs. degraded), false-Match gate banner, error list. |
| 403 / 404 / 500 | US-13 | Short explanation and a way back. |

## 5. Wireframe: report (desktop)
```
┌ VeriDoc ─────────────────────────────── Queue  Accuracy  Sign out ┐
│ VD-2026-00007 · Priya Raman · TN HSC                               │
│ [ ! Needs review — 2 issues ]                                      │
├──────────────────────────────────────┬────────────────────────────┤
│ Marks                                │  Mark sheet  [image]       │
│ Validation   Result      Details     │                            │
│ Mathematics  ✕ Mismatch  85 / 88     │  Photo       [image]       │
│ Physics      ✓ Match     92 / 92     │                            │
│ Completeness ✓ Pass      all present │                            │
│ Photo                                │                            │
│ Resolution   ✕ Fail      180×220 …   │                            │
├──────────────────────────────────────┤                            │
│ Decision: (•) Approve ( ) Reject ( ) Request re-upload            │
│ Comment [..........................]  [Record decision]          │
└──────────────────────────────────────┴────────────────────────────┘
```

## 6. Responsive and accessibility
- **Breakpoints:** 360 / 768 / 1280 px. Below 900 px, two-column layouts stack.
- Every input has a `<label>`. Errors are linked with `aria-describedby`. Focus ring is a 3 px `--brand` outline.
- Respects `prefers-reduced-motion`. The only motion is the step transition, which is instant.
- Status is never shown by colour alone.

## 7. Review against the brief
- One memorable element: the **Entered / Uploaded columns with tabular figures and a strong mismatch row**. Everything else stays quiet.
- Plan check: no generic SaaS card grid, no cream/terracotta palette, no all-caps eyebrows. ✔
